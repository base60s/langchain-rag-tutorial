"""
Excel parser for extracting balance sheet data from Excel files.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from uuid import uuid4
import re

try:
    import pandas as pd
    import openpyxl
    from openpyxl.utils.dataframe import dataframe_to_rows
except ImportError as e:
    logging.warning(f"Excel parsing dependencies not available: {e}")

from .base_parser import BaseParser, ParsingResult
from ..models.document import DocumentMetadata, DocumentChunk, DocumentFormat


class ExcelParser(BaseParser):
    """Parser for Excel financial documents."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.XLSX, DocumentFormat.XLS]
        self.logger = logging.getLogger(__name__)
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given Excel file."""
        return file_path.suffix.lower() in ['.xlsx', '.xls']
    
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsingResult:
        """Parse Excel document and extract financial data."""
        try:
            result = ParsingResult(success=False)
            
            # Read all sheets from the Excel file
            try:
                # Try to read with openpyxl first (better for .xlsx)
                all_sheets = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            except:
                try:
                    # Fallback to xlrd for .xls files
                    all_sheets = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
                except Exception as e:
                    result.errors.append(f"Failed to read Excel file: {str(e)}")
                    return result
            
            if not all_sheets:
                result.errors.append("No sheets found in Excel file")
                return result
            
            # Process each sheet
            all_chunks = []
            all_tables = []
            all_figures = []
            all_balance_sheet_items = {'assets': [], 'liabilities': [], 'equity': []}
            
            for sheet_name, df in all_sheets.items():
                sheet_result = self._process_sheet(df, sheet_name)
                
                if sheet_result['chunks']:
                    all_chunks.extend(sheet_result['chunks'])
                if sheet_result['tables']:
                    all_tables.extend(sheet_result['tables'])
                if sheet_result['figures']:
                    all_figures.extend(sheet_result['figures'])
                if sheet_result['balance_sheet_items']:
                    for category in ['assets', 'liabilities', 'equity']:
                        all_balance_sheet_items[category].extend(
                            sheet_result['balance_sheet_items'].get(category, [])
                        )
            
            # Identify the most likely balance sheet
            balance_sheet_info = self._identify_balance_sheet(all_sheets)
            
            result.success = True
            result.chunks = all_chunks
            result.tables = all_tables
            result.figures = all_figures
            result.metadata = {
                'sheet_count': len(all_sheets),
                'sheet_names': list(all_sheets.keys()),
                'balance_sheet_sheet': balance_sheet_info['sheet_name'],
                'balance_sheet_confidence': balance_sheet_info['confidence'],
                'balance_sheet_items': all_balance_sheet_items,
                'file_format': file_path.suffix.lower()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing Excel {file_path}: {str(e)}")
            return ParsingResult(
                success=False,
                errors=[f"Excel parsing failed: {str(e)}"]
            )
    
    def _process_sheet(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """Process a single Excel sheet."""
        result = {
            'chunks': [],
            'tables': [],
            'figures': [],
            'balance_sheet_items': {'assets': [], 'liabilities': [], 'equity': []}
        }
        
        if df.empty:
            return result
        
        # Clean the dataframe
        df_cleaned = self._clean_dataframe(df)
        
        # Convert dataframe to text for general processing
        sheet_text = self._dataframe_to_text(df_cleaned)
        
        # Create chunks from the sheet text
        text_chunks = self._split_into_chunks(sheet_text)
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                document_id=uuid4(),
                chunk_index=i,
                text=chunk_text,
                section_type=f"sheet_{sheet_name}",
                financial_figures=self.extract_financial_figures(chunk_text)
            )
            result['chunks'].append(chunk)
        
        # Extract structured table data
        table_data = self._extract_table_from_dataframe(df_cleaned, sheet_name)
        if table_data:
            result['tables'].append(table_data)
        
        # Extract financial figures
        result['figures'] = self.extract_financial_figures(sheet_text)
        
        # Extract balance sheet items
        result['balance_sheet_items'] = self._extract_balance_sheet_from_dataframe(df_cleaned)
        
        return result
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the dataframe by removing empty rows/columns and handling NaN values."""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Fill NaN values with empty strings for text processing
        df = df.fillna('')
        
        # Convert all values to strings for consistent processing
        df = df.astype(str)
        
        return df
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """Convert dataframe to text format."""
        text_lines = []
        
        # Add header if it exists
        if not df.columns.empty:
            header = '\t'.join(str(col) for col in df.columns)
            text_lines.append(header)
        
        # Add rows
        for _, row in df.iterrows():
            row_text = '\t'.join(str(cell) for cell in row)
            if row_text.strip():  # Only add non-empty rows
                text_lines.append(row_text)
        
        return '\n'.join(text_lines)
    
    def _extract_table_from_dataframe(self, df: pd.DataFrame, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Extract structured table data from dataframe."""
        if df.empty:
            return None
        
        # Convert dataframe to table format
        table = {
            'sheet_name': sheet_name,
            'headers': list(df.columns),
            'rows': df.values.tolist(),
            'row_count': len(df),
            'column_count': len(df.columns),
            'is_financial': False,
            'financial_data': None
        }
        
        # Check if this is a financial table
        table['is_financial'] = self._is_financial_dataframe(df)
        
        if table['is_financial']:
            table['financial_data'] = self._extract_financial_data_from_dataframe(df)
        
        return table
    
    def _is_financial_dataframe(self, df: pd.DataFrame) -> bool:
        """Determine if a dataframe contains financial data."""
        if df.empty:
            return False
        
        # Check column headers for financial terms
        headers = [str(col).lower() for col in df.columns]
        financial_header_terms = [
            'assets', 'liabilities', 'equity', 'amount', 'balance', 
            'total', 'current', 'long-term', 'cash', 'receivables',
            'inventory', 'debt', 'capital', 'earnings', 'year'
        ]
        
        has_financial_headers = any(
            any(term in header for term in financial_header_terms)
            for header in headers
        )
        
        # Check first column for financial line items
        if not df.empty and len(df.columns) > 0:
            first_column_text = ' '.join(str(val).lower() for val in df.iloc[:, 0])
            has_financial_items = any(
                term in first_column_text 
                for term in ['cash', 'receivable', 'inventory', 'payable', 'debt', 'equity']
            )
        else:
            has_financial_items = False
        
        # Check for numeric data that looks like financial figures
        has_financial_numbers = False
        for col in df.columns[1:]:  # Skip first column (usually labels)
            try:
                # Try to convert to numeric
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                if not numeric_col.isna().all():
                    # Check if values are in typical financial ranges
                    max_val = numeric_col.max()
                    if max_val > 1000:  # Assume financial figures are > 1000
                        has_financial_numbers = True
                        break
            except:
                continue
        
        return has_financial_headers or (has_financial_items and has_financial_numbers)
    
    def _extract_financial_data_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract structured financial data from dataframe."""
        financial_data = {
            'line_items': [],
            'totals': {},
            'currency': 'USD',
            'scale': 'units'
        }
        
        if df.empty:
            return financial_data
        
        # Assume first column contains line item names
        item_column = 0
        amount_columns = list(range(1, len(df.columns)))
        
        # Process each row
        for _, row in df.iterrows():
            item_name = str(row.iloc[item_column]).strip()
            if not item_name or item_name.lower() in ['', 'nan', 'none']:
                continue
            
            # Extract amounts from amount columns
            amounts = []
            for col_idx in amount_columns:
                if col_idx < len(row):
                    cell_value = str(row.iloc[col_idx])
                    # Try to extract financial figures
                    figures = self.extract_financial_figures(cell_value)
                    amounts.extend(figures)
            
            if amounts or self._is_balance_sheet_line_item(item_name):
                # Categorize the line item
                category = self._categorize_balance_sheet_item(item_name)
                
                financial_data['line_items'].append({
                    'name': item_name,
                    'category': category,
                    'amounts': amounts,
                    'raw_row': row.tolist()
                })
                
                # Check for totals
                if 'total' in item_name.lower():
                    financial_data['totals'][item_name.lower()] = amounts
        
        return financial_data
    
    def _extract_balance_sheet_from_dataframe(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Extract balance sheet items from dataframe."""
        items = {
            'assets': [],
            'liabilities': [],
            'equity': []
        }
        
        if df.empty:
            return items
        
        # Process each row looking for balance sheet items
        for _, row in df.iterrows():
            if len(row) == 0:
                continue
                
            item_name = str(row.iloc[0]).strip()
            if not item_name or item_name.lower() in ['', 'nan', 'none']:
                continue
            
            # Check if this is a balance sheet line item
            if self._is_balance_sheet_line_item(item_name):
                category = self._categorize_balance_sheet_item(item_name)
                
                # Extract amounts from the row
                amounts = []
                row_text = ' '.join(str(cell) for cell in row[1:])
                amounts = self.extract_financial_figures(row_text)
                
                item_data = {
                    'name': item_name,
                    'category': category,
                    'amounts': amounts,
                    'row_data': row.tolist()
                }
                
                # Categorize into assets, liabilities, or equity
                if category.startswith('asset_'):
                    items['assets'].append(item_data)
                elif category.startswith('liability_'):
                    items['liabilities'].append(item_data)
                elif category.startswith('equity_'):
                    items['equity'].append(item_data)
        
        return items
    
    def _is_balance_sheet_line_item(self, item_name: str) -> bool:
        """Check if an item name represents a balance sheet line item."""
        item_lower = item_name.lower()
        
        balance_sheet_terms = [
            'cash', 'receivable', 'inventory', 'asset', 'property', 'equipment',
            'payable', 'debt', 'liability', 'loan', 'obligation',
            'equity', 'capital', 'earnings', 'retained', 'stock', 'share'
        ]
        
        return any(term in item_lower for term in balance_sheet_terms)
    
    def _categorize_balance_sheet_item(self, item_name: str) -> str:
        """Categorize a balance sheet line item."""
        item_lower = item_name.lower()
        
        # Check against predefined patterns
        for category, patterns in self.asset_patterns.items():
            for pattern in patterns:
                if re.search(pattern, item_lower):
                    return f"asset_{category.value}"
        
        for category, patterns in self.liability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, item_lower):
                    return f"liability_{category.value}"
        
        for category, patterns in self.equity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, item_lower):
                    return f"equity_{category.value}"
        
        # General categorization
        if any(term in item_lower for term in ['asset', 'cash', 'receivable', 'inventory', 'property', 'equipment']):
            return "asset_other"
        elif any(term in item_lower for term in ['liability', 'payable', 'debt', 'loan', 'obligation']):
            return "liability_other"
        elif any(term in item_lower for term in ['equity', 'capital', 'earnings', 'retained', 'stock']):
            return "equity_other"
        else:
            return "unknown"
    
    def _identify_balance_sheet(self, all_sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Identify which sheet is most likely the balance sheet."""
        sheet_scores = {}
        
        for sheet_name, df in all_sheets.items():
            score = 0
            
            # Check sheet name
            sheet_name_lower = sheet_name.lower()
            if 'balance' in sheet_name_lower and 'sheet' in sheet_name_lower:
                score += 50
            elif 'balance' in sheet_name_lower:
                score += 30
            elif any(term in sheet_name_lower for term in ['bs', 'bsheet', 'position']):
                score += 20
            
            # Check content
            if not df.empty:
                sheet_text = self._dataframe_to_text(df).lower()
                
                # Look for balance sheet terms
                balance_sheet_terms = ['assets', 'liabilities', 'equity', 'current assets', 'long-term debt']
                for term in balance_sheet_terms:
                    if term in sheet_text:
                        score += 10
                
                # Look for balance sheet structure
                if 'total assets' in sheet_text and 'total liabilities' in sheet_text:
                    score += 30
                
                # Check if it looks like financial data
                if self._is_financial_dataframe(df):
                    score += 20
            
            sheet_scores[sheet_name] = score
        
        # Find the sheet with the highest score
        if sheet_scores:
            best_sheet = max(sheet_scores, key=sheet_scores.get)
            confidence = sheet_scores[best_sheet] / 100.0  # Normalize to 0-1
            return {
                'sheet_name': best_sheet,
                'confidence': min(confidence, 1.0),
                'all_scores': sheet_scores
            }
        else:
            return {
                'sheet_name': None,
                'confidence': 0.0,
                'all_scores': {}
            }
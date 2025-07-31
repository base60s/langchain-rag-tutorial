"""
CSV parser for extracting balance sheet data from CSV files.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4
import csv
import re

try:
    import pandas as pd
    import chardet
except ImportError as e:
    logging.warning(f"CSV parsing dependencies not available: {e}")

from .base_parser import BaseParser, ParsingResult
from ..models.document import DocumentMetadata, DocumentChunk, DocumentFormat


class CSVParser(BaseParser):
    """Parser for CSV financial documents."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.CSV]
        self.logger = logging.getLogger(__name__)
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given CSV file."""
        return file_path.suffix.lower() == '.csv'
    
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsingResult:
        """Parse CSV document and extract financial data."""
        try:
            result = ParsingResult(success=False)
            
            # Detect file encoding
            encoding = self._detect_encoding(file_path)
            
            # Try different CSV reading approaches
            df = self._read_csv_with_fallbacks(file_path, encoding)
            
            if df is None or df.empty:
                result.errors.append("Failed to read CSV file or file is empty")
                return result
            
            # Clean the dataframe
            df_cleaned = self._clean_dataframe(df)
            
            # Convert to text for processing
            csv_text = self._dataframe_to_text(df_cleaned)
            
            # Create chunks
            text_chunks = self._split_into_chunks(csv_text)
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    document_id=uuid4(),
                    chunk_index=i,
                    text=chunk_text,
                    section_type="csv_data",
                    financial_figures=self.extract_financial_figures(chunk_text)
                )
                chunks.append(chunk)
            
            # Extract table structure
            table_data = self._extract_table_from_dataframe(df_cleaned)
            
            # Extract financial figures
            all_figures = self.extract_financial_figures(csv_text)
            
            # Extract balance sheet items
            balance_sheet_items = self._extract_balance_sheet_from_dataframe(df_cleaned)
            
            # Analyze CSV structure
            structure_analysis = self._analyze_csv_structure(df_cleaned)
            
            result.success = True
            result.chunks = chunks
            result.tables = [table_data] if table_data else []
            result.figures = all_figures
            result.metadata = {
                'encoding': encoding,
                'row_count': len(df_cleaned),
                'column_count': len(df_cleaned.columns),
                'columns': list(df_cleaned.columns),
                'structure_analysis': structure_analysis,
                'balance_sheet_items': balance_sheet_items,
                'scale': self.detect_scale(csv_text)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing CSV {file_path}: {str(e)}")
            return ParsingResult(
                success=False,
                errors=[f"CSV parsing failed: {str(e)}"]
            )
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect the encoding of the CSV file."""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                
                # Common fallbacks for financial files
                if encoding is None or result.get('confidence', 0) < 0.7:
                    # Try common encodings for financial files
                    for test_encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            with open(file_path, 'r', encoding=test_encoding) as test_file:
                                test_file.read(1000)  # Try to read first 1KB
                                return test_encoding
                        except:
                            continue
                    return 'utf-8'  # Final fallback
                
                return encoding
        except Exception:
            return 'utf-8'  # Default fallback
    
    def _read_csv_with_fallbacks(self, file_path: Path, encoding: str) -> Optional[pd.DataFrame]:
        """Try to read CSV with different parameters."""
        read_attempts = [
            # Standard approach
            {'encoding': encoding, 'sep': ','},
            # Try semicolon separator (common in European files)
            {'encoding': encoding, 'sep': ';'},
            # Try tab separator
            {'encoding': encoding, 'sep': '\t'},
            # Try with different encoding
            {'encoding': 'latin-1', 'sep': ','},
            # Try auto-detection
            {'encoding': encoding, 'sep': None},
            # Try with error handling
            {'encoding': encoding, 'sep': ',', 'error_bad_lines': False},
        ]
        
        for params in read_attempts:
            try:
                # Remove None values for pandas compatibility
                clean_params = {k: v for k, v in params.items() if v is not None}
                df = pd.read_csv(file_path, **clean_params)
                
                if not df.empty and len(df.columns) > 1:
                    return df
            except Exception as e:
                self.logger.debug(f"CSV read attempt failed with params {params}: {e}")
                continue
        
        return None
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the dataframe."""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Fill NaN values with empty strings
        df = df.fillna('')
        
        # Convert all values to strings for consistent processing
        df = df.astype(str)
        
        # Remove rows where all values are empty strings
        df = df[~(df == '').all(axis=1)]
        
        return df
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """Convert dataframe to text format."""
        text_lines = []
        
        # Add header
        if not df.columns.empty:
            header = ','.join(str(col) for col in df.columns)
            text_lines.append(header)
        
        # Add rows
        for _, row in df.iterrows():
            row_text = ','.join(str(cell) for cell in row)
            if row_text.strip() and row_text != ',' * (len(row) - 1):  # Skip empty rows
                text_lines.append(row_text)
        
        return '\n'.join(text_lines)
    
    def _extract_table_from_dataframe(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Extract table structure from dataframe."""
        if df.empty:
            return None
        
        table = {
            'headers': list(df.columns),
            'rows': df.values.tolist(),
            'row_count': len(df),
            'column_count': len(df.columns),
            'is_financial': False,
            'financial_data': None
        }
        
        # Check if this is financial data
        table['is_financial'] = self._is_financial_dataframe(df)
        
        if table['is_financial']:
            table['financial_data'] = self._extract_financial_data_from_dataframe(df)
        
        return table
    
    def _is_financial_dataframe(self, df: pd.DataFrame) -> bool:
        """Determine if dataframe contains financial data."""
        if df.empty:
            return False
        
        # Check headers for financial terms
        headers = [str(col).lower() for col in df.columns]
        financial_header_terms = [
            'assets', 'liabilities', 'equity', 'amount', 'balance', 
            'total', 'current', 'long-term', 'cash', 'receivables',
            'inventory', 'debt', 'capital', 'earnings', 'value'
        ]
        
        has_financial_headers = any(
            any(term in header for term in financial_header_terms)
            for header in headers
        )
        
        # Check content for financial terms
        if not df.empty:
            # Check first column for financial line items
            first_column_text = ' '.join(str(val).lower() for val in df.iloc[:, 0][:10])  # First 10 rows
            has_financial_items = any(
                term in first_column_text 
                for term in ['cash', 'receivable', 'inventory', 'payable', 'debt', 'equity', 'asset', 'liability']
            )
            
            # Check for numeric data patterns
            has_large_numbers = False
            for col in df.columns[1:]:  # Skip first column
                try:
                    # Try to find numeric patterns
                    col_text = ' '.join(str(val) for val in df[col][:5])
                    figures = self.extract_financial_figures(col_text)
                    if figures and any(float(fig['amount']) > 1000 for fig in figures):
                        has_large_numbers = True
                        break
                except:
                    continue
        else:
            has_financial_items = False
            has_large_numbers = False
        
        return has_financial_headers or (has_financial_items and has_large_numbers)
    
    def _extract_financial_data_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract financial data from dataframe."""
        financial_data = {
            'line_items': [],
            'totals': {},
            'currency': 'USD',
            'scale': 'units'
        }
        
        if df.empty:
            return financial_data
        
        # Detect scale from content
        all_text = self._dataframe_to_text(df)
        financial_data['scale'] = self.detect_scale(all_text)
        
        # Process each row
        for _, row in df.iterrows():
            if len(row) == 0:
                continue
                
            # First column typically contains item names
            item_name = str(row.iloc[0]).strip()
            if not item_name or item_name.lower() in ['', 'nan', 'none']:
                continue
            
            # Extract amounts from remaining columns
            amounts = []
            for col_idx in range(1, len(row)):
                if col_idx < len(row):
                    cell_value = str(row.iloc[col_idx])
                    figures = self.extract_financial_figures(cell_value)
                    amounts.extend(figures)
            
            # Only include rows with financial significance
            if amounts or self._is_balance_sheet_line_item(item_name):
                category = self._categorize_balance_sheet_item(item_name)
                
                financial_data['line_items'].append({
                    'name': item_name,
                    'category': category,
                    'amounts': amounts,
                    'raw_row': row.tolist()
                })
                
                # Track totals
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
        
        for _, row in df.iterrows():
            if len(row) == 0:
                continue
                
            item_name = str(row.iloc[0]).strip()
            if not item_name or item_name.lower() in ['', 'nan', 'none']:
                continue
            
            if self._is_balance_sheet_line_item(item_name):
                category = self._categorize_balance_sheet_item(item_name)
                
                # Extract amounts
                amounts = []
                row_text = ' '.join(str(cell) for cell in row[1:])
                amounts = self.extract_financial_figures(row_text)
                
                item_data = {
                    'name': item_name,
                    'category': category,
                    'amounts': amounts,
                    'row_data': row.tolist()
                }
                
                # Categorize
                if category.startswith('asset_'):
                    items['assets'].append(item_data)
                elif category.startswith('liability_'):
                    items['liabilities'].append(item_data)
                elif category.startswith('equity_'):
                    items['equity'].append(item_data)
        
        return items
    
    def _is_balance_sheet_line_item(self, item_name: str) -> bool:
        """Check if item name represents a balance sheet line item."""
        item_lower = item_name.lower()
        
        balance_sheet_terms = [
            'cash', 'receivable', 'inventory', 'asset', 'property', 'equipment',
            'investment', 'goodwill', 'intangible',
            'payable', 'debt', 'liability', 'loan', 'obligation', 'accrued',
            'equity', 'capital', 'earnings', 'retained', 'stock', 'share'
        ]
        
        return any(term in item_lower for term in balance_sheet_terms)
    
    def _categorize_balance_sheet_item(self, item_name: str) -> str:
        """Categorize balance sheet line item."""
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
        if any(term in item_lower for term in ['asset', 'cash', 'receivable', 'inventory', 'property', 'equipment', 'investment']):
            return "asset_other"
        elif any(term in item_lower for term in ['liability', 'payable', 'debt', 'loan', 'obligation', 'accrued']):
            return "liability_other"
        elif any(term in item_lower for term in ['equity', 'capital', 'earnings', 'retained', 'stock']):
            return "equity_other"
        else:
            return "unknown"
    
    def _analyze_csv_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze the structure and characteristics of the CSV data."""
        analysis = {
            'likely_balance_sheet': False,
            'confidence_score': 0,
            'structure_type': 'unknown',
            'time_series': False,
            'multi_period': False,
            'identified_sections': []
        }
        
        if df.empty:
            return analysis
        
        # Check for balance sheet indicators
        all_text = self._dataframe_to_text(df).lower()
        
        # Balance sheet terms
        bs_terms = ['assets', 'liabilities', 'equity', 'balance sheet']
        bs_score = sum(10 for term in bs_terms if term in all_text)
        
        # Structure analysis
        if len(df.columns) > 2:
            # Check if columns represent time periods
            columns = [str(col) for col in df.columns[1:]]  # Skip first column
            date_like_columns = sum(1 for col in columns if any(char.isdigit() for char in col))
            
            if date_like_columns >= 2:
                analysis['time_series'] = True
                analysis['multi_period'] = True
                bs_score += 15
        
        # Check first column for balance sheet line items
        if not df.empty:
            first_col_items = [str(val).lower() for val in df.iloc[:, 0][:20]]  # First 20 items
            bs_items = sum(1 for item in first_col_items if self._is_balance_sheet_line_item(item))
            
            if bs_items >= 5:  # At least 5 balance sheet items
                analysis['likely_balance_sheet'] = True
                bs_score += 20
        
        # Look for section headers
        sections = []
        for _, row in df.iterrows():
            item_name = str(row.iloc[0]).lower().strip()
            if any(term in item_name for term in ['assets', 'current assets', 'non-current assets']):
                sections.append('assets')
            elif any(term in item_name for term in ['liabilities', 'current liabilities', 'long-term']):
                sections.append('liabilities')  
            elif any(term in item_name for term in ['equity', 'shareholders equity', 'stockholders']):
                sections.append('equity')
        
        analysis['identified_sections'] = list(set(sections))
        if len(sections) >= 2:
            bs_score += 25
        
        # Determine structure type
        if analysis['likely_balance_sheet']:
            analysis['structure_type'] = 'balance_sheet'
        elif analysis['time_series']:
            analysis['structure_type'] = 'time_series_financial'
        elif self._is_financial_dataframe(df):
            analysis['structure_type'] = 'financial_data'
        else:
            analysis['structure_type'] = 'general_data'
        
        analysis['confidence_score'] = min(bs_score / 100.0, 1.0)
        analysis['likely_balance_sheet'] = analysis['confidence_score'] > 0.3
        
        return analysis
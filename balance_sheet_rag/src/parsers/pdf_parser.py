"""
PDF parser for extracting balance sheet data from PDF documents.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import uuid4
import tempfile
import os
import re

try:
    import pdfplumber
    import pypdf2
    from PIL import Image
    import pytesseract
except ImportError as e:
    logging.warning(f"PDF parsing dependencies not available: {e}")

from .base_parser import BaseParser, ParsingResult
from ..models.document import DocumentMetadata, DocumentChunk, DocumentFormat


class PDFParser(BaseParser):
    """Parser for PDF financial documents."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentFormat.PDF]
        self.logger = logging.getLogger(__name__)
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given PDF file."""
        return file_path.suffix.lower() == '.pdf'
    
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsingResult:
        """Parse PDF document and extract financial data."""
        try:
            result = ParsingResult(success=False)
            
            # Try pdfplumber first (better for structured PDFs)
            text_content = self._extract_with_pdfplumber(file_path)
            
            if not text_content or len(text_content.strip()) < 100:
                # Fallback to PyPDF2
                text_content = self._extract_with_pypdf2(file_path)
            
            if not text_content or len(text_content.strip()) < 100:
                # Last resort: OCR
                text_content = self._extract_with_ocr(file_path)
                if text_content:
                    result.warnings.append("Text extracted using OCR - accuracy may be lower")
            
            if not text_content:
                result.errors.append("Failed to extract text from PDF")
                return result
            
            # Clean the extracted text
            cleaned_text = self._clean_text(text_content)
            
            # Split into chunks
            text_chunks = self._split_into_chunks(cleaned_text)
            
            # Create document chunks
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    document_id=uuid4(),  # Will be updated by the calling code
                    chunk_index=i,
                    text=chunk_text,
                    financial_figures=self.extract_financial_figures(chunk_text)
                )
                chunks.append(chunk)
            
            # Extract tables
            tables = self._extract_tables_from_pdf(file_path)
            
            # Extract financial figures from the entire document
            all_figures = self.extract_financial_figures(cleaned_text)
            
            # Extract balance sheet items
            balance_sheet_items = self.extract_balance_sheet_items(cleaned_text)
            
            # Detect document structure
            document_structure = self._analyze_document_structure(cleaned_text)
            
            result.success = True
            result.chunks = chunks
            result.tables = tables
            result.figures = all_figures
            result.metadata = {
                'page_count': self._get_page_count(file_path),
                'scale': self.detect_scale(cleaned_text),
                'dates': self.extract_dates(cleaned_text),
                'balance_sheet_items': balance_sheet_items,
                'document_structure': document_structure,
                'extraction_method': self._determine_extraction_method(file_path)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            return ParsingResult(
                success=False,
                errors=[f"PDF parsing failed: {str(e)}"]
            )
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber (best for structured PDFs)."""
        try:
            text_content = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            return '\n'.join(text_content)
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed: {e}")
            return ""
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2 (fallback method)."""
        try:
            text_content = []
            with open(file_path, 'rb') as file:
                reader = pypdf2.PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            return '\n'.join(text_content)
        except Exception as e:
            self.logger.warning(f"PyPDF2 extraction failed: {e}")
            return ""
    
    def _extract_with_ocr(self, file_path: Path) -> str:
        """Extract text using OCR (for scanned PDFs)."""
        try:
            import fitz  # PyMuPDF for PDF to image conversion
            
            text_content = []
            pdf_document = fitz.open(file_path)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                
                # Convert page to image
                pix = page.get_pixmap()
                img_data = pix.tobytes("ppm")
                
                # Create temporary image file
                with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as temp_file:
                    temp_file.write(img_data)
                    temp_path = temp_file.name
                
                try:
                    # Extract text using OCR
                    text = pytesseract.image_to_string(Image.open(temp_path))
                    if text.strip():
                        text_content.append(text)
                finally:
                    # Clean up temporary file
                    os.unlink(temp_path)
            
            pdf_document.close()
            return '\n'.join(text_content)
            
        except Exception as e:
            self.logger.warning(f"OCR extraction failed: {e}")
            return ""
    
    def _extract_tables_from_pdf(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract tables from PDF using pdfplumber."""
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table_num, table in enumerate(page_tables):
                        if table and len(table) > 1:  # Must have header and at least one data row
                            # Process table data
                            processed_table = {
                                'page': page_num + 1,
                                'table_index': table_num,
                                'headers': table[0] if table else [],
                                'rows': table[1:] if len(table) > 1 else [],
                                'row_count': len(table) - 1 if len(table) > 1 else 0,
                                'column_count': len(table[0]) if table and table[0] else 0
                            }
                            
                            # Try to identify if this is a financial table
                            is_financial = self._is_financial_table(processed_table)
                            processed_table['is_financial'] = is_financial
                            
                            if is_financial:
                                # Extract financial data from table
                                financial_data = self._extract_financial_data_from_table(processed_table)
                                processed_table['financial_data'] = financial_data
                            
                            tables.append(processed_table)
        
        except Exception as e:
            self.logger.warning(f"Table extraction failed: {e}")
        
        return tables
    
    def _is_financial_table(self, table: Dict[str, Any]) -> bool:
        """Determine if a table contains financial data."""
        if not table.get('headers') or not table.get('rows'):
            return False
        
        # Check headers for financial terms
        headers = [str(h).lower() for h in table['headers'] if h]
        financial_header_terms = [
            'assets', 'liabilities', 'equity', 'amount', 'balance', 
            'total', 'current', 'long-term', 'cash', 'receivables',
            'inventory', 'debt', 'capital', 'earnings'
        ]
        
        has_financial_headers = any(
            any(term in header for term in financial_header_terms)
            for header in headers
        )
        
        # Check for currency symbols or large numbers in data
        has_financial_data = False
        for row in table['rows'][:5]:  # Check first 5 rows
            row_text = ' '.join(str(cell) for cell in row if cell)
            if self.extract_financial_figures(row_text):
                has_financial_data = True
                break
        
        return has_financial_headers or has_financial_data
    
    def _extract_financial_data_from_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured financial data from a table."""
        financial_data = {
            'line_items': [],
            'totals': {},
            'currency': 'USD',
            'scale': 'units'
        }
        
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        # Try to identify column structure
        amount_columns = []
        for i, header in enumerate(headers):
            if header and any(term in str(header).lower() for term in ['amount', 'balance', '2023', '2022', 'current', 'year']):
                amount_columns.append(i)
        
        # Extract line items
        for row in rows:
            if not row or not any(row):
                continue
            
            # First column usually contains the line item name
            item_name = str(row[0]) if row and row[0] else ""
            if not item_name.strip():
                continue
            
            # Extract amounts from identified amount columns
            amounts = []
            for col_idx in amount_columns:
                if col_idx < len(row) and row[col_idx]:
                    cell_text = str(row[col_idx])
                    figures = self.extract_financial_figures(cell_text)
                    amounts.extend(figures)
            
            if amounts:
                # Categorize the line item
                category = self._categorize_line_item(item_name)
                
                financial_data['line_items'].append({
                    'name': item_name.strip(),
                    'category': category,
                    'amounts': amounts,
                    'raw_row': row
                })
        
        return financial_data
    
    def _categorize_line_item(self, item_name: str) -> str:
        """Categorize a balance sheet line item."""
        item_lower = item_name.lower()
        
        # Check against our predefined patterns
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
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze the structure of the document to identify sections."""
        structure = {
            'sections': [],
            'has_balance_sheet': False,
            'has_income_statement': False,
            'has_cash_flow': False
        }
        
        # Look for section headers
        lines = text.split('\n')
        section_patterns = {
            'balance_sheet': [
                r'balance\s+sheet',
                r'statement\s+of\s+financial\s+position',
                r'consolidated\s+balance\s+sheet'
            ],
            'income_statement': [
                r'income\s+statement',
                r'statement\s+of\s+operations',
                r'profit\s+and\s+loss'
            ],
            'cash_flow': [
                r'cash\s+flow',
                r'statement\s+of\s+cash\s+flows'
            ]
        }
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            for section_type, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        structure['sections'].append({
                            'type': section_type,
                            'title': line.strip(),
                            'line_number': i,
                            'start_position': text.find(line)
                        })
                        structure[f'has_{section_type}'] = True
                        break
        
        return structure
    
    def _get_page_count(self, file_path: Path) -> int:
        """Get the number of pages in the PDF."""
        try:
            with pdfplumber.open(file_path) as pdf:
                return len(pdf.pages)
        except:
            try:
                with open(file_path, 'rb') as file:
                    reader = pypdf2.PdfReader(file)
                    return len(reader.pages)
            except:
                return 0
    
    def _determine_extraction_method(self, file_path: Path) -> str:
        """Determine which extraction method was most successful."""
        # This is a simplified version - in practice, you'd track which method was used
        return "pdfplumber"
"""
Base parser class for financial document parsing.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field

from ..models.document import DocumentMetadata, DocumentChunk
from ..models.balance_sheet import AssetCategory, LiabilityCategory, EquityCategory


class ParsingResult(BaseModel):
    """Result of document parsing operation."""
    
    success: bool = Field(..., description="Whether parsing was successful")
    chunks: List[DocumentChunk] = Field(default_factory=list, description="Extracted document chunks")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted tables")
    figures: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted financial figures")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    errors: List[str] = Field(default_factory=list, description="Parsing errors")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")


class BaseParser(ABC):
    """Base class for all document parsers."""
    
    def __init__(self):
        self.supported_formats = []
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup regex patterns for financial data extraction."""
        # Currency patterns
        self.currency_patterns = {
            'usd': re.compile(r'\$\s*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE),
            'eur': re.compile(r'€\s*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE),
            'gbp': re.compile(r'£\s*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE),
            'generic': re.compile(r'([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE)
        }
        
        # Financial term patterns
        self.asset_patterns = {
            AssetCategory.CASH_AND_EQUIVALENTS: [
                r'cash\s+and\s+cash\s+equivalents',
                r'cash\s+equivalents',
                r'cash',
                r'short.term\s+investments',
                r'marketable\s+securities'
            ],
            AssetCategory.ACCOUNTS_RECEIVABLE: [
                r'accounts\s+receivable',
                r'receivables',
                r'trade\s+receivables',
                r'net\s+receivables'
            ],
            AssetCategory.INVENTORY: [
                r'inventory',
                r'inventories',
                r'raw\s+materials',
                r'work\s+in\s+process',
                r'finished\s+goods'
            ],
            AssetCategory.PROPERTY_PLANT_EQUIPMENT: [
                r'property,?\s+plant\s+and\s+equipment',
                r'ppe',
                r'fixed\s+assets',
                r'plant\s+and\s+equipment'
            ]
        }
        
        self.liability_patterns = {
            LiabilityCategory.ACCOUNTS_PAYABLE: [
                r'accounts\s+payable',
                r'trade\s+payables',
                r'payables'
            ],
            LiabilityCategory.SHORT_TERM_DEBT: [
                r'short.term\s+debt',
                r'current\s+portion.*debt',
                r'notes\s+payable'
            ],
            LiabilityCategory.LONG_TERM_DEBT: [
                r'long.term\s+debt',
                r'debt.*long.term',
                r'bonds\s+payable'
            ]
        }
        
        self.equity_patterns = {
            EquityCategory.SHARE_CAPITAL: [
                r'common\s+stock',
                r'share\s+capital',
                r'capital\s+stock',
                r'ordinary\s+shares'
            ],
            EquityCategory.RETAINED_EARNINGS: [
                r'retained\s+earnings',
                r'accumulated\s+earnings',
                r'earnings\s+retained'
            ]
        }
        
        # Scale patterns (thousands, millions, billions)
        self.scale_patterns = {
            'thousands': re.compile(r'(?:in\s+)?thousands?', re.IGNORECASE),
            'millions': re.compile(r'(?:in\s+)?millions?', re.IGNORECASE),
            'billions': re.compile(r'(?:in\s+)?billions?', re.IGNORECASE)
        }
        
        # Date patterns
        self.date_patterns = [
            re.compile(r'(\d{4})-(\d{2})-(\d{2})'),  # YYYY-MM-DD
            re.compile(r'(\d{2})/(\d{2})/(\d{4})'),  # MM/DD/YYYY
            re.compile(r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', re.IGNORECASE),
        ]
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsingResult:
        """Parse the document and extract financial data."""
        pass
    
    def extract_financial_figures(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial figures from text."""
        figures = []
        
        # Extract currency amounts
        for currency, pattern in self.currency_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                try:
                    # Clean the number (remove commas)
                    clean_number = match.replace(',', '')
                    amount = Decimal(clean_number)
                    
                    figures.append({
                        'amount': amount,
                        'currency': currency.upper() if currency != 'generic' else 'USD',
                        'raw_text': match,
                        'context': self._get_context(text, match)
                    })
                except (InvalidOperation, ValueError):
                    continue
        
        return figures
    
    def extract_balance_sheet_items(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract balance sheet line items from text."""
        items = {
            'assets': [],
            'liabilities': [],
            'equity': []
        }
        
        # Extract assets
        for category, patterns in self.asset_patterns.items():
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.finditer(text)
                for match in matches:
                    # Look for associated amounts
                    context = self._get_context(text, match.group(), window=100)
                    amounts = self.extract_financial_figures(context)
                    
                    if amounts:
                        items['assets'].append({
                            'name': match.group(),
                            'category': category.value,
                            'amounts': amounts,
                            'position': match.start()
                        })
        
        # Extract liabilities
        for category, patterns in self.liability_patterns.items():
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.finditer(text)
                for match in matches:
                    context = self._get_context(text, match.group(), window=100)
                    amounts = self.extract_financial_figures(context)
                    
                    if amounts:
                        items['liabilities'].append({
                            'name': match.group(),
                            'category': category.value,
                            'amounts': amounts,
                            'position': match.start()
                        })
        
        # Extract equity
        for category, patterns in self.equity_patterns.items():
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.finditer(text)
                for match in matches:
                    context = self._get_context(text, match.group(), window=100)
                    amounts = self.extract_financial_figures(context)
                    
                    if amounts:
                        items['equity'].append({
                            'name': match.group(),
                            'category': category.value,
                            'amounts': amounts,
                            'position': match.start()
                        })
        
        return items
    
    def detect_scale(self, text: str) -> str:
        """Detect the scale of financial figures (thousands, millions, billions)."""
        for scale, pattern in self.scale_patterns.items():
            if pattern.search(text):
                return scale
        return 'units'
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        dates = []
        for pattern in self.date_patterns:
            matches = pattern.findall(text)
            dates.extend([match if isinstance(match, str) else '-'.join(match) for match in matches])
        return dates
    
    def detect_table_structure(self, text: str) -> List[Dict[str, Any]]:
        """Detect table-like structures in text."""
        lines = text.split('\n')
        tables = []
        
        current_table = []
        for line in lines:
            # Simple heuristic: if line has multiple numbers/currency amounts, it might be a table row
            amounts = self.extract_financial_figures(line)
            if len(amounts) >= 2:  # At least 2 financial figures
                current_table.append({
                    'text': line.strip(),
                    'amounts': amounts
                })
            else:
                if len(current_table) >= 3:  # At least 3 rows to be considered a table
                    tables.append({
                        'rows': current_table,
                        'row_count': len(current_table)
                    })
                current_table = []
        
        # Don't forget the last table
        if len(current_table) >= 3:
            tables.append({
                'rows': current_table,
                'row_count': len(current_table)
            })
        
        return tables
    
    def _get_context(self, text: str, term: str, window: int = 50) -> str:
        """Get context around a term in text."""
        position = text.lower().find(term.lower())
        if position == -1:
            return ""
        
        start = max(0, position - window)
        end = min(len(text), position + len(term) + window)
        return text[start:end]
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove non-printable characters
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
        return text.strip()
    
    def _split_into_chunks(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', end - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def validate_balance_sheet_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate extracted balance sheet data."""
        errors = []
        
        # Check for required sections
        required_sections = ['assets', 'liabilities', 'equity']
        for section in required_sections:
            if section not in data or not data[section]:
                errors.append(f"Missing {section} section")
        
        # Check balance sheet equation (if totals are available)
        if 'totals' in data:
            totals = data['totals']
            total_assets = totals.get('total_assets', 0)
            total_liabilities = totals.get('total_liabilities', 0)
            total_equity = totals.get('total_equity', 0)
            
            if abs(total_assets - (total_liabilities + total_equity)) > 0.01:
                errors.append("Balance sheet equation not balanced: Assets ≠ Liabilities + Equity")
        
        return len(errors) == 0, errors
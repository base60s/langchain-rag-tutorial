"""
Document models for financial document processing and metadata management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of financial documents."""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW_STATEMENT = "cash_flow_statement"
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    SEC_FILING_10K = "sec_filing_10k"
    SEC_FILING_10Q = "sec_filing_10q"
    SEC_FILING_8K = "sec_filing_8k"
    EARNINGS_REPORT = "earnings_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    OTHER = "other"


class DocumentFormat(str, Enum):
    """Document file formats."""
    PDF = "pdf"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    XML = "xml"
    XBRL = "xbrl"
    HTML = "html"
    TXT = "txt"
    DOC = "doc"
    DOCX = "docx"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class DocumentSource(str, Enum):
    """Source of the document."""
    MANUAL_UPLOAD = "manual_upload"
    SEC_EDGAR = "sec_edgar"
    COMPANY_WEBSITE = "company_website"
    FINANCIAL_API = "financial_api"
    EMAIL_IMPORT = "email_import"
    SCANNER = "scanner"
    OTHER = "other"


class DocumentMetadata(BaseModel):
    """Metadata for financial documents."""
    
    id: UUID = Field(default_factory=uuid4)
    filename: str = Field(..., description="Original filename")
    document_type: DocumentType = Field(..., description="Type of financial document")
    document_format: DocumentFormat = Field(..., description="File format")
    source: DocumentSource = Field(..., description="Source of the document")
    
    # Company information
    company_name: Optional[str] = Field(None, description="Company name")
    company_ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    company_cik: Optional[str] = Field(None, description="SEC CIK number")
    
    # Financial period information
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, description="Fiscal quarter (1-4)")
    period_end_date: Optional[str] = Field(None, description="Period end date (YYYY-MM-DD)")
    reporting_date: Optional[str] = Field(None, description="Date document was reported/filed")
    
    # Document properties
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    page_count: Optional[int] = Field(None, description="Number of pages")
    language: str = Field(default="en", description="Document language")
    currency: str = Field(default="USD", description="Currency used in document")
    
    # Processing information
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_start_time: Optional[datetime] = Field(None)
    processing_end_time: Optional[datetime] = Field(None)
    
    # Extracted information
    contains_balance_sheet: bool = Field(default=False)
    contains_income_statement: bool = Field(default=False)
    contains_cash_flow: bool = Field(default=False)
    tables_detected: int = Field(default=0)
    
    # Quality metrics
    text_extraction_quality: Optional[float] = Field(None, description="Quality score 0-1")
    ocr_confidence: Optional[float] = Field(None, description="OCR confidence 0-1")
    data_completeness: Optional[float] = Field(None, description="Data completeness 0-1")
    
    # Custom tags and notes
    tags: List[str] = Field(default_factory=list, description="Custom tags")
    notes: Optional[str] = Field(None, description="Processing notes")
    error_messages: List[str] = Field(default_factory=list, description="Error messages during processing")
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "AAPL_10K_2023.pdf",
                "document_type": "sec_filing_10k",
                "document_format": "pdf",
                "source": "sec_edgar",
                "company_name": "Apple Inc.",
                "company_ticker": "AAPL",
                "fiscal_year": 2023,
                "period_end_date": "2023-09-30",
                "language": "en",
                "currency": "USD",
                "processing_status": "completed",
                "contains_balance_sheet": True,
                "contains_income_statement": True,
                "contains_cash_flow": True,
                "tables_detected": 15,
                "text_extraction_quality": 0.95,
                "tags": ["annual", "technology", "large-cap"]
            }
        }


class DocumentChunk(BaseModel):
    """Individual chunk of processed document."""
    
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID = Field(..., description="Parent document ID")
    chunk_index: int = Field(..., description="Index of chunk in document")
    
    # Content
    text: str = Field(..., description="Extracted text content")
    page_number: Optional[int] = Field(None, description="Source page number")
    section_type: Optional[str] = Field(None, description="Section type (e.g., 'balance_sheet', 'notes')")
    
    # Position information
    start_char: Optional[int] = Field(None, description="Start character position in document")
    end_char: Optional[int] = Field(None, description="End character position in document")
    
    # Structured data (if extracted)
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted tables")
    financial_figures: List[Dict[str, Any]] = Field(default_factory=list, description="Identified financial figures")
    
    # Metadata
    chunk_type: str = Field(default="text", description="Type of chunk (text, table, figure)")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    class Config:
        schema_extra = {
            "example": {
                "chunk_index": 0,
                "text": "Current assets: Cash and cash equivalents $29,965 million...",
                "page_number": 45,
                "section_type": "balance_sheet",
                "start_char": 1250,
                "end_char": 1750,
                "chunk_type": "text"
            }
        }


class ProcessedDocument(BaseModel):
    """Complete processed document with all chunks and extracted data."""
    
    id: UUID = Field(default_factory=uuid4)
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    
    # Processed content
    chunks: List[DocumentChunk] = Field(default_factory=list, description="Document chunks")
    full_text: Optional[str] = Field(None, description="Complete extracted text")
    
    # Extracted structured data
    balance_sheet_data: Optional[Dict[str, Any]] = Field(None, description="Extracted balance sheet data")
    income_statement_data: Optional[Dict[str, Any]] = Field(None, description="Extracted income statement data")
    cash_flow_data: Optional[Dict[str, Any]] = Field(None, description="Extracted cash flow data")
    
    # Document structure
    table_of_contents: List[Dict[str, Any]] = Field(default_factory=list, description="Document structure")
    sections: List[Dict[str, Any]] = Field(default_factory=list, description="Document sections")
    
    # Processing results
    processing_log: List[str] = Field(default_factory=list, description="Processing log messages")
    validation_results: Dict[str, Any] = Field(default_factory=dict, description="Data validation results")
    
    def get_chunks_by_section(self, section_type: str) -> List[DocumentChunk]:
        """Get chunks by section type."""
        return [chunk for chunk in self.chunks if chunk.section_type == section_type]
    
    def get_financial_figures(self) -> List[Dict[str, Any]]:
        """Get all financial figures from all chunks."""
        figures = []
        for chunk in self.chunks:
            figures.extend(chunk.financial_figures)
        return figures
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """Get all tables from all chunks."""
        tables = []
        for chunk in self.chunks:
            tables.extend(chunk.tables)
        return tables
    
    def calculate_processing_time(self) -> Optional[float]:
        """Calculate total processing time in seconds."""
        if (self.metadata.processing_start_time and 
            self.metadata.processing_end_time):
            delta = self.metadata.processing_end_time - self.metadata.processing_start_time
            return delta.total_seconds()
        return None
    
    class Config:
        schema_extra = {
            "example": {
                "metadata": {
                    "filename": "AAPL_10K_2023.pdf",
                    "document_type": "sec_filing_10k",
                    "processing_status": "completed"
                },
                "chunks": [],
                "processing_log": [
                    "Started processing",
                    "Extracted 150 pages",
                    "Identified 12 financial tables",
                    "Processing completed successfully"
                ]
            }
        }


class DocumentProcessingRequest(BaseModel):
    """Request model for document processing."""
    
    file_path: str = Field(..., description="Path to the document file")
    document_type: Optional[DocumentType] = Field(None, description="Expected document type")
    company_name: Optional[str] = Field(None, description="Company name")
    company_ticker: Optional[str] = Field(None, description="Stock ticker")
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, description="Fiscal quarter")
    
    # Processing options
    extract_tables: bool = Field(default=True, description="Extract tables from document")
    use_ocr: bool = Field(default=True, description="Use OCR for scanned documents")
    validate_data: bool = Field(default=True, description="Validate extracted financial data")
    create_embeddings: bool = Field(default=True, description="Create vector embeddings")
    
    # Custom processing parameters
    chunk_size: int = Field(default=500, description="Text chunk size for embeddings")
    chunk_overlap: int = Field(default=100, description="Text chunk overlap")
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "/uploads/AAPL_10K_2023.pdf",
                "document_type": "sec_filing_10k",
                "company_ticker": "AAPL",
                "fiscal_year": 2023,
                "extract_tables": True,
                "use_ocr": True,
                "validate_data": True,
                "create_embeddings": True
            }
        }


class DocumentSearchQuery(BaseModel):
    """Query model for document search."""
    
    query_text: str = Field(..., description="Search query")
    document_types: Optional[List[DocumentType]] = Field(None, description="Filter by document types")
    company_tickers: Optional[List[str]] = Field(None, description="Filter by company tickers")
    fiscal_years: Optional[List[int]] = Field(None, description="Filter by fiscal years")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")
    
    # Search parameters
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold for search")
    max_results: int = Field(default=10, description="Maximum number of results")
    include_metadata: bool = Field(default=True, description="Include document metadata in results")
    
    class Config:
        schema_extra = {
            "example": {
                "query_text": "current assets and cash equivalents",
                "document_types": ["balance_sheet", "sec_filing_10k"],
                "company_tickers": ["AAPL", "MSFT"],
                "fiscal_years": [2022, 2023],
                "similarity_threshold": 0.7,
                "max_results": 10
            }
        }
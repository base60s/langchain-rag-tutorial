"""
Configuration settings for the Balance Sheet RAG system.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///./balance_sheet_rag.db", description="Database URL")
    echo: bool = Field(default=False, description="Echo SQL queries")
    
    class Config:
        env_prefix = "DB_"


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""
    
    provider: str = Field(default="openai", description="Embedding provider")
    model: str = Field(default="text-embedding-3-large", description="Embedding model name")
    chunk_size: int = Field(default=500, description="Text chunk size for embeddings")
    chunk_overlap: int = Field(default=100, description="Text chunk overlap")
    batch_size: int = Field(default=100, description="Embedding batch size")
    
    class Config:
        env_prefix = "EMBEDDING_"


class LLMSettings(BaseSettings):
    """Language model configuration."""
    
    provider: str = Field(default="openai", description="LLM provider")
    model: str = Field(default="gpt-4", description="LLM model name")
    temperature: float = Field(default=0.1, description="LLM temperature")
    max_tokens: int = Field(default=2000, description="Maximum tokens in response")
    
    class Config:
        env_prefix = "LLM_"


class VectorStoreSettings(BaseSettings):
    """Vector store configuration."""
    
    provider: str = Field(default="chroma", description="Vector store provider")
    persist_directory: str = Field(default="./data/vectorstore", description="Vector store persistence directory")
    collection_name: str = Field(default="balance_sheets", description="Vector store collection name")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold for retrieval")
    top_k: int = Field(default=10, description="Number of documents to retrieve")
    
    class Config:
        env_prefix = "VECTORSTORE_"


class APISettings(BaseSettings):
    """API configuration settings."""
    
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    
    class Config:
        env_prefix = "API_"


class ExternalAPISettings(BaseSettings):
    """External API keys and settings."""
    
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    alpha_vantage_api_key: Optional[str] = Field(default=None, description="Alpha Vantage API key")
    financial_modeling_prep_api_key: Optional[str] = Field(default=None, description="Financial Modeling Prep API key")
    
    class Config:
        env_prefix = "EXTERNAL_"


class ProcessingSettings(BaseSettings):
    """Document processing settings."""
    
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    supported_formats: List[str] = Field(
        default=["pdf", "xlsx", "xls", "csv", "xml", "txt"],
        description="Supported file formats"
    )
    ocr_enabled: bool = Field(default=True, description="Enable OCR for scanned documents")
    parallel_processing: bool = Field(default=True, description="Enable parallel document processing")
    
    class Config:
        env_prefix = "PROCESSING_"


class FinancialSettings(BaseSettings):
    """Financial analysis settings."""
    
    default_currency: str = Field(default="USD", description="Default currency")
    financial_year_end: str = Field(default="12-31", description="Default financial year end (MM-DD)")
    industry_benchmarks_enabled: bool = Field(default=True, description="Enable industry benchmarking")
    ratio_calculation_precision: int = Field(default=4, description="Decimal precision for ratio calculations")
    
    class Config:
        env_prefix = "FINANCIAL_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file_path: Optional[str] = Field(default="./logs/balance_sheet_rag.log", description="Log file path")
    
    class Config:
        env_prefix = "LOG_"


class Settings(BaseSettings):
    """Main application settings."""
    
    app_name: str = Field(default="Balance Sheet RAG", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    llm: LLMSettings = LLMSettings()
    vectorstore: VectorStoreSettings = VectorStoreSettings()
    api: APISettings = APISettings()
    external_apis: ExternalAPISettings = ExternalAPISettings()
    processing: ProcessingSettings = ProcessingSettings()
    financial: FinancialSettings = FinancialSettings()
    logging: LoggingSettings = LoggingSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
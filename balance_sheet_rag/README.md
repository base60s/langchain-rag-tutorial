# Balance Sheet RAG System

A comprehensive Retrieval-Augmented Generation (RAG) system specifically designed for balance sheet analysis and financial document processing. This system combines advanced document parsing, financial domain knowledge, and intelligent query processing to provide detailed insights into company financial positions.

## 🚀 Features

### Document Processing
- **Multi-format Support**: PDF, Excel (.xlsx, .xls), CSV, XML, and XBRL files
- **Intelligent Parsing**: Automatic detection and extraction of balance sheet data
- **OCR Support**: Handle scanned financial documents with OCR capabilities
- **Table Extraction**: Sophisticated table detection and financial data extraction
- **XBRL Processing**: Native support for XBRL financial filings (SEC 10-K, 10-Q)

### Financial Analysis
- **Balance Sheet Recognition**: Automatic categorization of assets, liabilities, and equity
- **Financial Ratios**: Comprehensive calculation of liquidity, leverage, efficiency, and profitability ratios
- **Multi-period Analysis**: Compare financial data across different reporting periods
- **Industry Benchmarking**: Compare metrics against industry standards
- **Financial Health Scoring**: Altman Z-Score and Piotroski F-Score calculations

### Advanced RAG Capabilities
- **Financial Domain Embeddings**: Specialized embeddings for financial terminology
- **Context-Aware Queries**: Understand complex financial relationships and calculations
- **Structured Responses**: Generate detailed analysis with supporting calculations
- **Source Attribution**: Track and cite source documents for all analysis

### API & Integration
- **REST API**: Full-featured API for integration with other systems
- **Real-time Processing**: Process and analyze documents in real-time
- **Batch Processing**: Handle large volumes of financial documents
- **Export Capabilities**: Generate reports in PDF, Excel, and other formats

## 📁 Project Structure

```
balance_sheet_rag/
├── src/
│   ├── core/              # Core business logic
│   ├── parsers/           # Document parsers (PDF, Excel, CSV, XML)
│   ├── models/            # Data models and schemas
│   ├── api/               # REST API endpoints
│   ├── utils/             # Utility functions
│   └── analysis/          # Financial analysis and calculations
├── data/
│   ├── raw/               # Raw financial documents
│   ├── processed/         # Processed document chunks
│   └── sample/            # Sample documents for testing
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                  # Documentation
├── config/                # Configuration files
├── notebooks/             # Jupyter notebooks for analysis
└── requirements.txt       # Python dependencies
```

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- PostgreSQL (optional, SQLite is used by default)
- Tesseract OCR (for scanned document processing)

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd balance_sheet_rag
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
# Install system dependencies for OCR (Ubuntu/Debian)
sudo apt-get install tesseract-ocr

# Install Python dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Create a `.env` file in the project root:

```bash
# OpenAI API Configuration
EXTERNAL_OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (optional)
DB_URL=sqlite:///./balance_sheet_rag.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Vector Store Configuration
VECTORSTORE_PERSIST_DIRECTORY=./data/vectorstore

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/balance_sheet_rag.log
```

## 🚀 Quick Start

### 1. Basic Document Processing

```python
from src.parsers import PDFParser, ExcelParser
from src.models.document import DocumentProcessingRequest

# Process a PDF balance sheet
pdf_parser = PDFParser()
result = pdf_parser.parse("path/to/balance_sheet.pdf")

if result.success:
    print(f"Extracted {len(result.chunks)} text chunks")
    print(f"Found {len(result.tables)} tables")
    print(f"Detected {len(result.figures)} financial figures")

# Process an Excel balance sheet
excel_parser = ExcelParser()
result = excel_parser.parse("path/to/balance_sheet.xlsx")
```

### 2. Financial Ratio Analysis

```python
from src.analysis.ratio_calculator import FinancialRatioCalculator
from src.models.balance_sheet import BalanceSheet

# Calculate financial ratios
calculator = FinancialRatioCalculator()
ratios = calculator.calculate_all_ratios(balance_sheet)

print(f"Current Ratio: {ratios.liquidity_ratios.current_ratio}")
print(f"Debt-to-Equity: {ratios.leverage_ratios.debt_to_equity_ratio}")
print(f"ROE: {ratios.profitability_ratios.return_on_equity}")
```

### 3. Query Balance Sheet Data

```python
from src.core.query_engine import BalanceSheetQueryEngine

# Initialize query engine
query_engine = BalanceSheetQueryEngine()

# Ask natural language questions
response = query_engine.query(
    "What is the company's current ratio and how does it compare to the industry average?"
)

print(response.answer)
print(f"Sources: {response.sources}")
```

### 4. Start the API Server

```bash
# Start the FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the API documentation at `http://localhost:8000/docs`

## 📊 Supported Financial Metrics

### Liquidity Ratios
- Current Ratio
- Quick Ratio (Acid-Test)
- Cash Ratio
- Working Capital
- Working Capital Ratio

### Leverage Ratios
- Debt-to-Equity Ratio
- Debt Ratio
- Equity Ratio
- Equity Multiplier
- Long-term Debt to Equity

### Efficiency Ratios
- Asset Turnover
- Working Capital Turnover
- Receivables Turnover
- Inventory Turnover
- Fixed Asset Turnover

### Profitability Ratios
- Return on Assets (ROA)
- Return on Equity (ROE)
- Gross Margin
- Net Profit Margin
- Operating Margin

### Financial Health Metrics
- Altman Z-Score
- Piotroski F-Score
- DuPont Analysis

## 🔧 Configuration

The system uses a hierarchical configuration system with environment variables and configuration files. Key configuration areas:

### Database Settings
```python
DB_URL=postgresql://user:password@localhost/balance_sheet_rag
DB_ECHO=False
```

### Embedding Configuration
```python
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_CHUNK_SIZE=500
EMBEDDING_CHUNK_OVERLAP=100
```

### LLM Configuration
```python
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000
```

## 📚 API Documentation

### Process Document
```http
POST /api/v1/documents/process
Content-Type: multipart/form-data

{
  "file": <binary-file>,
  "document_type": "balance_sheet",
  "company_ticker": "AAPL",
  "fiscal_year": 2023
}
```

### Query Balance Sheet
```http
POST /api/v1/query
Content-Type: application/json

{
  "query": "What is the debt-to-equity ratio?",
  "company_ticker": "AAPL",
  "fiscal_year": 2023
}
```

### Calculate Ratios
```http
POST /api/v1/analysis/ratios
Content-Type: application/json

{
  "balance_sheet_id": "uuid-here",
  "ratio_types": ["liquidity", "leverage", "profitability"]
}
```

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Integration Tests
```bash
pytest tests/integration/ -v
```

### Run All Tests with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

## 📈 Performance Optimization

### Embedding Performance
- Use batch processing for large documents
- Implement caching for frequently accessed embeddings
- Consider GPU acceleration for large-scale processing

### Query Performance
- Enable database indexing for frequently queried fields
- Use connection pooling for database operations
- Implement query result caching

### Document Processing
- Enable parallel processing for multiple documents
- Use streaming for large file processing
- Implement progressive loading for large datasets

## 🔒 Security Considerations

- **API Authentication**: Implement JWT or API key authentication
- **Data Encryption**: Encrypt sensitive financial data at rest
- **Access Control**: Implement role-based access control
- **Audit Logging**: Log all financial data access and modifications
- **Input Validation**: Validate all user inputs and file uploads

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use type hints for all function signatures

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder for detailed documentation
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions for general questions

## 🚧 Roadmap

### Phase 1 (Current)
- ✅ Multi-format document parsing
- ✅ Basic financial ratio calculations
- ✅ REST API implementation
- 🔄 Enhanced embedding system

### Phase 2 (Next)
- ⏳ Machine learning models for anomaly detection
- ⏳ Real-time financial data integration
- ⏳ Advanced visualization dashboards
- ⏳ Multi-language support

### Phase 3 (Future)
- ⏳ Predictive financial modeling
- ⏳ ESG (Environmental, Social, Governance) analysis
- ⏳ Blockchain integration for document verification
- ⏳ Mobile application development

## 📊 Examples and Use Cases

### Investment Analysis
- Compare balance sheets across multiple companies
- Identify financial trends and patterns
- Generate investment recommendations based on financial health

### Risk Assessment
- Calculate bankruptcy probability using Altman Z-Score
- Identify liquidity and solvency risks
- Monitor key financial ratios over time

### Regulatory Compliance
- Process SEC filings and extract required metrics
- Generate regulatory reports
- Ensure compliance with financial reporting standards

### Financial Research
- Analyze industry-wide financial trends
- Research specific financial metrics across sectors
- Generate academic research data

---

**Built with ❤️ for the financial analysis community**
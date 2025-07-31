"""
Balance sheet data models and schemas.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AssetType(str, Enum):
    """Types of assets."""
    CURRENT = "current"
    NON_CURRENT = "non_current"


class AssetCategory(str, Enum):
    """Asset categories."""
    CASH_AND_EQUIVALENTS = "cash_and_equivalents"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    INVENTORY = "inventory" 
    PREPAID_EXPENSES = "prepaid_expenses"
    SHORT_TERM_INVESTMENTS = "short_term_investments"
    OTHER_CURRENT_ASSETS = "other_current_assets"
    
    PROPERTY_PLANT_EQUIPMENT = "property_plant_equipment"
    INTANGIBLE_ASSETS = "intangible_assets"
    LONG_TERM_INVESTMENTS = "long_term_investments"
    GOODWILL = "goodwill"
    OTHER_NON_CURRENT_ASSETS = "other_non_current_assets"


class LiabilityType(str, Enum):
    """Types of liabilities."""
    CURRENT = "current"
    NON_CURRENT = "non_current"


class LiabilityCategory(str, Enum):
    """Liability categories."""
    ACCOUNTS_PAYABLE = "accounts_payable"
    SHORT_TERM_DEBT = "short_term_debt"
    ACCRUED_LIABILITIES = "accrued_liabilities"
    DEFERRED_REVENUE = "deferred_revenue"
    OTHER_CURRENT_LIABILITIES = "other_current_liabilities"
    
    LONG_TERM_DEBT = "long_term_debt"
    DEFERRED_TAX_LIABILITIES = "deferred_tax_liabilities"
    PENSION_OBLIGATIONS = "pension_obligations"
    OTHER_NON_CURRENT_LIABILITIES = "other_non_current_liabilities"


class EquityCategory(str, Enum):
    """Equity categories."""
    SHARE_CAPITAL = "share_capital"
    RETAINED_EARNINGS = "retained_earnings"
    ADDITIONAL_PAID_IN_CAPITAL = "additional_paid_in_capital"
    ACCUMULATED_OTHER_COMPREHENSIVE_INCOME = "accumulated_other_comprehensive_income"
    TREASURY_STOCK = "treasury_stock"
    NON_CONTROLLING_INTERESTS = "non_controlling_interests"


class Company(BaseModel):
    """Company information model."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Company name")
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    cik: Optional[str] = Field(None, description="SEC CIK number")
    industry: Optional[str] = Field(None, description="Industry classification")
    sector: Optional[str] = Field(None, description="Sector classification")
    country: Optional[str] = Field(None, description="Country of incorporation")
    currency: str = Field(default="USD", description="Reporting currency")
    fiscal_year_end: Optional[str] = Field(None, description="Fiscal year end (MM-DD)")
    
    class Config:
        orm_mode = True


class FinancialPeriod(BaseModel):
    """Financial reporting period."""
    id: UUID = Field(default_factory=uuid4)
    period_end_date: date = Field(..., description="Period end date")
    period_type: str = Field(..., description="Period type (annual, quarterly)")
    fiscal_year: int = Field(..., description="Fiscal year")
    fiscal_quarter: Optional[int] = Field(None, description="Fiscal quarter (1-4)")
    
    class Config:
        orm_mode = True


class Asset(BaseModel):
    """Asset line item model."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Asset name")
    category: AssetCategory = Field(..., description="Asset category")
    asset_type: AssetType = Field(..., description="Current or non-current")
    amount: Decimal = Field(..., description="Asset amount")
    percentage_of_total: Optional[Decimal] = Field(None, description="Percentage of total assets")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Asset amount must be positive')
        return v
    
    class Config:
        orm_mode = True


class Liability(BaseModel):
    """Liability line item model."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Liability name")
    category: LiabilityCategory = Field(..., description="Liability category")
    liability_type: LiabilityType = Field(..., description="Current or non-current")
    amount: Decimal = Field(..., description="Liability amount")
    percentage_of_total: Optional[Decimal] = Field(None, description="Percentage of total liabilities")
    maturity_date: Optional[date] = Field(None, description="Maturity date for debt")
    interest_rate: Optional[Decimal] = Field(None, description="Interest rate for debt")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Liability amount must be positive')
        return v
    
    class Config:
        orm_mode = True


class Equity(BaseModel):
    """Equity line item model."""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Equity name")
    category: EquityCategory = Field(..., description="Equity category")
    amount: Decimal = Field(..., description="Equity amount")
    percentage_of_total: Optional[Decimal] = Field(None, description="Percentage of total equity")
    shares_outstanding: Optional[int] = Field(None, description="Number of shares outstanding")
    par_value: Optional[Decimal] = Field(None, description="Par value per share")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        orm_mode = True


class BalanceSheet(BaseModel):
    """Complete balance sheet model."""
    id: UUID = Field(default_factory=uuid4)
    company: Company = Field(..., description="Company information")
    period: FinancialPeriod = Field(..., description="Financial period")
    
    # Assets
    assets: List[Asset] = Field(default_factory=list, description="All assets")
    total_current_assets: Decimal = Field(default=Decimal("0"), description="Total current assets")
    total_non_current_assets: Decimal = Field(default=Decimal("0"), description="Total non-current assets")
    total_assets: Decimal = Field(default=Decimal("0"), description="Total assets")
    
    # Liabilities
    liabilities: List[Liability] = Field(default_factory=list, description="All liabilities")
    total_current_liabilities: Decimal = Field(default=Decimal("0"), description="Total current liabilities")
    total_non_current_liabilities: Decimal = Field(default=Decimal("0"), description="Total non-current liabilities")
    total_liabilities: Decimal = Field(default=Decimal("0"), description="Total liabilities")
    
    # Equity
    equity_items: List[Equity] = Field(default_factory=list, description="All equity items")
    total_equity: Decimal = Field(default=Decimal("0"), description="Total equity")
    
    # Balance sheet equation validation
    total_liabilities_and_equity: Decimal = Field(default=Decimal("0"), description="Total liabilities and equity")
    
    # Metadata
    currency: str = Field(default="USD", description="Currency")
    scale: str = Field(default="units", description="Scale (units, thousands, millions)")
    source: Optional[str] = Field(None, description="Data source")
    filing_date: Optional[date] = Field(None, description="Filing date")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('total_liabilities_and_equity', always=True)
    def calculate_total_liabilities_and_equity(cls, v, values):
        total_liab = values.get('total_liabilities', Decimal("0"))
        total_eq = values.get('total_equity', Decimal("0"))
        return total_liab + total_eq
    
    @validator('total_assets', always=True)
    def validate_balance_sheet_equation(cls, v, values):
        total_liab_eq = values.get('total_liabilities_and_equity', Decimal("0"))
        if abs(v - total_liab_eq) > Decimal("0.01"):  # Allow for rounding differences
            raise ValueError(f"Balance sheet equation not balanced: Assets {v} != Liabilities + Equity {total_liab_eq}")
        return v
    
    def calculate_totals(self):
        """Calculate all totals from line items."""
        # Calculate asset totals
        current_assets = sum(asset.amount for asset in self.assets if asset.asset_type == AssetType.CURRENT)
        non_current_assets = sum(asset.amount for asset in self.assets if asset.asset_type == AssetType.NON_CURRENT)
        
        self.total_current_assets = current_assets
        self.total_non_current_assets = non_current_assets
        self.total_assets = current_assets + non_current_assets
        
        # Calculate liability totals
        current_liabilities = sum(liability.amount for liability in self.liabilities if liability.liability_type == LiabilityType.CURRENT)
        non_current_liabilities = sum(liability.amount for liability in self.liabilities if liability.liability_type == LiabilityType.NON_CURRENT)
        
        self.total_current_liabilities = current_liabilities
        self.total_non_current_liabilities = non_current_liabilities
        self.total_liabilities = current_liabilities + non_current_liabilities
        
        # Calculate equity total
        self.total_equity = sum(equity.amount for equity in self.equity_items)
        
        # Calculate total liabilities and equity
        self.total_liabilities_and_equity = self.total_liabilities + self.total_equity
        
        # Update timestamp
        self.updated_at = datetime.utcnow()
    
    def get_working_capital(self) -> Decimal:
        """Calculate working capital (Current Assets - Current Liabilities)."""
        return self.total_current_assets - self.total_current_liabilities
    
    def get_asset_by_category(self, category: AssetCategory) -> List[Asset]:
        """Get assets by category."""
        return [asset for asset in self.assets if asset.category == category]
    
    def get_liability_by_category(self, category: LiabilityCategory) -> List[Liability]:
        """Get liabilities by category."""
        return [liability for liability in self.liabilities if liability.category == category]
    
    def get_equity_by_category(self, category: EquityCategory) -> List[Equity]:
        """Get equity items by category."""
        return [equity for equity in self.equity_items if equity.category == category]
    
    class Config:
        orm_mode = True


# SQLAlchemy ORM Models for persistence
class CompanyORM(Base):
    __tablename__ = "companies"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    cik = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    country = Column(String, nullable=True)
    currency = Column(String, default="USD")
    fiscal_year_end = Column(String, nullable=True)
    
    balance_sheets = relationship("BalanceSheetORM", back_populates="company")


class FinancialPeriodORM(Base):
    __tablename__ = "financial_periods"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    period_end_date = Column(Date, nullable=False)
    period_type = Column(String, nullable=False)
    fiscal_year = Column(String, nullable=False)
    fiscal_quarter = Column(String, nullable=True)


class BalanceSheetORM(Base):
    __tablename__ = "balance_sheets"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    period_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("financial_periods.id"), nullable=False)
    
    # Totals
    total_current_assets = Column(Numeric(precision=15, scale=2), default=0)
    total_non_current_assets = Column(Numeric(precision=15, scale=2), default=0)
    total_assets = Column(Numeric(precision=15, scale=2), default=0)
    total_current_liabilities = Column(Numeric(precision=15, scale=2), default=0)
    total_non_current_liabilities = Column(Numeric(precision=15, scale=2), default=0)
    total_liabilities = Column(Numeric(precision=15, scale=2), default=0)
    total_equity = Column(Numeric(precision=15, scale=2), default=0)
    total_liabilities_and_equity = Column(Numeric(precision=15, scale=2), default=0)
    
    # Metadata
    currency = Column(String, default="USD")
    scale = Column(String, default="units")
    source = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("CompanyORM", back_populates="balance_sheets")
    period = relationship("FinancialPeriodORM")
    assets = relationship("AssetORM", back_populates="balance_sheet")
    liabilities = relationship("LiabilityORM", back_populates="balance_sheet")
    equity_items = relationship("EquityORM", back_populates="balance_sheet")


class AssetORM(Base):
    __tablename__ = "assets"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    balance_sheet_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("balance_sheets.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    percentage_of_total = Column(Numeric(precision=5, scale=2), nullable=True)
    notes = Column(Text, nullable=True)
    
    balance_sheet = relationship("BalanceSheetORM", back_populates="assets")


class LiabilityORM(Base):
    __tablename__ = "liabilities"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    balance_sheet_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("balance_sheets.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    liability_type = Column(String, nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    percentage_of_total = Column(Numeric(precision=5, scale=2), nullable=True)
    maturity_date = Column(Date, nullable=True)
    interest_rate = Column(Numeric(precision=5, scale=4), nullable=True)
    notes = Column(Text, nullable=True)
    
    balance_sheet = relationship("BalanceSheetORM", back_populates="liabilities")


class EquityORM(Base):
    __tablename__ = "equity"
    
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid4)
    balance_sheet_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("balance_sheets.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    percentage_of_total = Column(Numeric(precision=5, scale=2), nullable=True)
    shares_outstanding = Column(Numeric(precision=15, scale=0), nullable=True)
    par_value = Column(Numeric(precision=10, scale=4), nullable=True)
    notes = Column(Text, nullable=True)
    
    balance_sheet = relationship("BalanceSheetORM", back_populates="equity_items")
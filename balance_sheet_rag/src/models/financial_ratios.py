"""
Financial ratio models and calculations for balance sheet analysis.
"""
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class LiquidityRatios(BaseModel):
    """Liquidity ratio calculations."""
    
    current_ratio: Optional[Decimal] = Field(None, description="Current Assets / Current Liabilities")
    quick_ratio: Optional[Decimal] = Field(None, description="(Current Assets - Inventory) / Current Liabilities")
    cash_ratio: Optional[Decimal] = Field(None, description="Cash and Cash Equivalents / Current Liabilities")
    working_capital: Optional[Decimal] = Field(None, description="Current Assets - Current Liabilities")
    working_capital_ratio: Optional[Decimal] = Field(None, description="Working Capital / Total Assets")
    
    class Config:
        schema_extra = {
            "example": {
                "current_ratio": 2.5,
                "quick_ratio": 1.8,
                "cash_ratio": 0.5,
                "working_capital": 1000000.0,
                "working_capital_ratio": 0.15
            }
        }


class LeverageRatios(BaseModel):
    """Leverage and solvency ratio calculations."""
    
    debt_to_equity_ratio: Optional[Decimal] = Field(None, description="Total Debt / Total Equity")
    debt_ratio: Optional[Decimal] = Field(None, description="Total Debt / Total Assets")
    equity_ratio: Optional[Decimal] = Field(None, description="Total Equity / Total Assets")
    debt_to_assets_ratio: Optional[Decimal] = Field(None, description="Total Liabilities / Total Assets")
    equity_multiplier: Optional[Decimal] = Field(None, description="Total Assets / Total Equity")
    long_term_debt_to_equity: Optional[Decimal] = Field(None, description="Long-term Debt / Total Equity")
    times_interest_earned: Optional[Decimal] = Field(None, description="EBIT / Interest Expense (requires income statement)")
    
    class Config:
        schema_extra = {
            "example": {
                "debt_to_equity_ratio": 0.6,
                "debt_ratio": 0.4,
                "equity_ratio": 0.6,
                "debt_to_assets_ratio": 0.4,
                "equity_multiplier": 1.67,
                "long_term_debt_to_equity": 0.3
            }
        }


class EfficiencyRatios(BaseModel):
    """Asset efficiency and turnover ratios."""
    
    asset_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Total Assets (requires income statement)")
    working_capital_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Working Capital (requires income statement)")
    receivables_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Accounts Receivable (requires income statement)")
    inventory_turnover: Optional[Decimal] = Field(None, description="COGS / Average Inventory (requires income statement)")
    fixed_asset_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Fixed Assets (requires income statement)")
    total_asset_utilization: Optional[Decimal] = Field(None, description="Revenue / Total Assets (requires income statement)")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_turnover": 1.2,
                "working_capital_turnover": 4.5,
                "receivables_turnover": 8.0,
                "inventory_turnover": 6.0,
                "fixed_asset_turnover": 2.1
            }
        }


class ProfitabilityRatios(BaseModel):
    """Profitability ratios (requires income statement data)."""
    
    return_on_assets: Optional[Decimal] = Field(None, description="Net Income / Average Total Assets")
    return_on_equity: Optional[Decimal] = Field(None, description="Net Income / Average Total Equity")
    gross_margin: Optional[Decimal] = Field(None, description="Gross Profit / Revenue")
    net_profit_margin: Optional[Decimal] = Field(None, description="Net Income / Revenue")
    operating_margin: Optional[Decimal] = Field(None, description="Operating Income / Revenue")
    ebitda_margin: Optional[Decimal] = Field(None, description="EBITDA / Revenue")
    
    class Config:
        schema_extra = {
            "example": {
                "return_on_assets": 0.08,
                "return_on_equity": 0.12,
                "gross_margin": 0.35,
                "net_profit_margin": 0.06,
                "operating_margin": 0.10,
                "ebitda_margin": 0.15
            }
        }


class MarketRatios(BaseModel):
    """Market-based ratios (requires market data)."""
    
    book_value_per_share: Optional[Decimal] = Field(None, description="Total Equity / Shares Outstanding")
    tangible_book_value_per_share: Optional[Decimal] = Field(None, description="(Total Equity - Intangible Assets) / Shares Outstanding")
    price_to_book_ratio: Optional[Decimal] = Field(None, description="Market Price per Share / Book Value per Share")
    market_to_book_ratio: Optional[Decimal] = Field(None, description="Market Capitalization / Total Equity")
    
    class Config:
        schema_extra = {
            "example": {
                "book_value_per_share": 25.50,
                "tangible_book_value_per_share": 22.00,
                "price_to_book_ratio": 1.8,
                "market_to_book_ratio": 1.8
            }
        }


class DuPontAnalysis(BaseModel):
    """DuPont analysis breakdown of ROE."""
    
    roe: Optional[Decimal] = Field(None, description="Return on Equity")
    net_profit_margin: Optional[Decimal] = Field(None, description="Net Income / Revenue")
    asset_turnover: Optional[Decimal] = Field(None, description="Revenue / Average Total Assets")
    equity_multiplier: Optional[Decimal] = Field(None, description="Average Total Assets / Average Total Equity")
    
    @validator('roe')
    def validate_dupont_equation(cls, v, values):
        """Validate that ROE = Net Profit Margin × Asset Turnover × Equity Multiplier."""
        if v is not None:
            npm = values.get('net_profit_margin')
            at = values.get('asset_turnover')
            em = values.get('equity_multiplier')
            
            if all([npm, at, em]):
                calculated_roe = npm * at * em
                if abs(v - calculated_roe) > Decimal('0.001'):
                    raise ValueError(f"DuPont equation validation failed: ROE {v} != NPM×AT×EM {calculated_roe}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "roe": 0.15,
                "net_profit_margin": 0.08,
                "asset_turnover": 1.25,
                "equity_multiplier": 1.5
            }
        }


class FinancialHealthMetrics(BaseModel):
    """Overall financial health indicators."""
    
    altman_z_score: Optional[Decimal] = Field(None, description="Altman Z-Score for bankruptcy prediction")
    piotroski_f_score: Optional[int] = Field(None, description="Piotroski F-Score (0-9)")
    financial_strength_rating: Optional[str] = Field(None, description="Overall financial strength rating")
    
    # Individual components for Altman Z-Score
    working_capital_to_total_assets: Optional[Decimal] = Field(None, description="Working Capital / Total Assets")
    retained_earnings_to_total_assets: Optional[Decimal] = Field(None, description="Retained Earnings / Total Assets")
    ebit_to_total_assets: Optional[Decimal] = Field(None, description="EBIT / Total Assets")
    market_value_equity_to_book_value_debt: Optional[Decimal] = Field(None, description="Market Value of Equity / Book Value of Total Debt")
    sales_to_total_assets: Optional[Decimal] = Field(None, description="Sales / Total Assets")
    
    class Config:
        schema_extra = {
            "example": {
                "altman_z_score": 2.8,
                "piotroski_f_score": 7,
                "financial_strength_rating": "Strong",
                "working_capital_to_total_assets": 0.15,
                "retained_earnings_to_total_assets": 0.25,
                "ebit_to_total_assets": 0.12,
                "market_value_equity_to_book_value_debt": 1.5,
                "sales_to_total_assets": 0.8
            }
        }


class FinancialRatiosResult(BaseModel):
    """Complete financial ratios analysis result."""
    
    company_name: str = Field(..., description="Company name")
    ticker: Optional[str] = Field(None, description="Stock ticker")
    period_end_date: str = Field(..., description="Period end date")
    currency: str = Field(default="USD", description="Currency")
    
    # Ratio categories
    liquidity_ratios: LiquidityRatios = Field(default_factory=LiquidityRatios)
    leverage_ratios: LeverageRatios = Field(default_factory=LeverageRatios)
    efficiency_ratios: EfficiencyRatios = Field(default_factory=EfficiencyRatios)
    profitability_ratios: ProfitabilityRatios = Field(default_factory=ProfitabilityRatios)
    market_ratios: MarketRatios = Field(default_factory=MarketRatios)
    dupont_analysis: DuPontAnalysis = Field(default_factory=DuPontAnalysis)
    financial_health: FinancialHealthMetrics = Field(default_factory=FinancialHealthMetrics)
    
    # Metadata
    calculation_date: str = Field(..., description="Date when ratios were calculated")
    data_sources: list = Field(default_factory=list, description="Sources of data used")
    notes: Optional[str] = Field(None, description="Additional notes or limitations")
    
    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get key summary metrics."""
        return {
            "liquidity": {
                "current_ratio": self.liquidity_ratios.current_ratio,
                "quick_ratio": self.liquidity_ratios.quick_ratio,
                "working_capital": self.liquidity_ratios.working_capital
            },
            "leverage": {
                "debt_to_equity": self.leverage_ratios.debt_to_equity_ratio,
                "debt_ratio": self.leverage_ratios.debt_ratio,
                "equity_ratio": self.leverage_ratios.equity_ratio
            },
            "profitability": {
                "roe": self.profitability_ratios.return_on_equity,
                "roa": self.profitability_ratios.return_on_assets,
                "net_margin": self.profitability_ratios.net_profit_margin
            },
            "health": {
                "altman_z_score": self.financial_health.altman_z_score,
                "piotroski_f_score": self.financial_health.piotroski_f_score,
                "strength_rating": self.financial_health.financial_strength_rating
            }
        }
    
    def get_ratio_interpretation(self) -> Dict[str, str]:
        """Get interpretation of key ratios."""
        interpretations = {}
        
        # Current Ratio interpretation
        if self.liquidity_ratios.current_ratio:
            cr = float(self.liquidity_ratios.current_ratio)
            if cr > 2.5:
                interpretations["current_ratio"] = "Excellent liquidity, may indicate excess cash"
            elif cr > 1.5:
                interpretations["current_ratio"] = "Good liquidity position"
            elif cr > 1.0:
                interpretations["current_ratio"] = "Adequate liquidity"
            else:
                interpretations["current_ratio"] = "Poor liquidity, potential cash flow issues"
        
        # Debt-to-Equity interpretation
        if self.leverage_ratios.debt_to_equity_ratio:
            de = float(self.leverage_ratios.debt_to_equity_ratio)
            if de > 2.0:
                interpretations["debt_to_equity"] = "High leverage, higher financial risk"
            elif de > 1.0:
                interpretations["debt_to_equity"] = "Moderate leverage"
            elif de > 0.5:
                interpretations["debt_to_equity"] = "Conservative leverage"
            else:
                interpretations["debt_to_equity"] = "Low leverage, equity-heavy capital structure"
        
        # Altman Z-Score interpretation
        if self.financial_health.altman_z_score:
            z = float(self.financial_health.altman_z_score)
            if z > 2.99:
                interpretations["altman_z_score"] = "Low bankruptcy risk"
            elif z > 1.8:
                interpretations["altman_z_score"] = "Moderate bankruptcy risk"
            else:
                interpretations["altman_z_score"] = "High bankruptcy risk"
        
        return interpretations
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "period_end_date": "2023-09-30",
                "currency": "USD",
                "calculation_date": "2024-01-15",
                "data_sources": ["10-K Filing", "Yahoo Finance"],
                "notes": "All ratios calculated using GAAP accounting standards"
            }
        }
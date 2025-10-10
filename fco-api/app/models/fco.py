"""
FCO Analysis Pydantic Models
"""

from datetime import date, datetime
from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field, ConfigDict


class FCOAnalysisBase(BaseModel):
    """Base FCO analysis model"""
    symbol: str = Field(..., description="Symbol analyzed (e.g., SP500)")
    analysis_basis_date: date = Field(..., description="Analysis basis date (end of data period)")
    data_source: str = Field(..., description="Data source (fred/twelvedata)")
    data_period_start: date = Field(..., description="Start of data period")
    data_period_end: date = Field(..., description="End of data period")
    data_points: int = Field(..., description="Number of data points")


class FCOIndicators(BaseModel):
    """DS-LPPLS Indicators"""
    ds_lppls_confidence: Optional[float] = Field(None, ge=0, le=1, description="DS-LPPLS Confidence (0-1)")
    ds_lppls_confidence_neg: Optional[float] = Field(None, ge=0, le=1, description="DS-LPPLS Confidence Negative")
    ds_lppls_trust: Optional[float] = Field(None, ge=0, le=1, description="DS-LPPLS Trust indicator")
    ds_lppls_trust_negative: Optional[float] = Field(None, ge=0, le=1, description="DS-LPPLS Trust Negative")
    bubble_type: Optional[str] = Field(None, description="Detected bubble type")


class ClusteringResult(BaseModel):
    """Clustering analysis result"""
    predicted_tc: Optional[float] = Field(None, description="Predicted critical time (days)")
    tc_std: Optional[float] = Field(None, description="Standard deviation of tc")
    scenario_probability: Optional[float] = Field(None, ge=0, le=1, description="Scenario probability")
    cluster_method: Optional[str] = Field(default="dbscan", description="Clustering method used")


class MultiWindowInfo(BaseModel):
    """Multi-window analysis information"""
    num_windows: Optional[int] = Field(None, description="Number of time windows analyzed")
    num_qualified_fits: Optional[int] = Field(None, description="Number of qualified fits")
    window_min: Optional[int] = Field(None, description="Minimum window size")
    window_max: Optional[int] = Field(None, description="Maximum window size")
    window_step: Optional[int] = Field(None, description="Window step size")


class FCOAnalysisCreate(FCOAnalysisBase, FCOIndicators, ClusteringResult, MultiWindowInfo):
    """FCO analysis creation model"""
    filter_damping_min: float = Field(default=1.0, description="Minimum damping filter")
    filter_m_range: str = Field(default="[0.1, 0.9]", description="m parameter range")
    filter_omega_range: str = Field(default="[2, 25]", description="Omega range")
    
    predicted_crash_date: Optional[date] = Field(None, description="Predicted crash date")
    days_to_crash: Optional[int] = Field(None, description="Days to predicted crash")
    confidence_interval: Optional[str] = Field(None, description="Confidence interval")
    
    analysis_method: str = Field(default="FCO", description="Analysis method")
    engine_version: str = Field(default="v2.1", description="Engine version")
    computation_time_seconds: Optional[float] = Field(None, description="Computation time")


class FCOAnalysisResponse(FCOAnalysisBase, FCOIndicators, ClusteringResult, MultiWindowInfo):
    """FCO analysis response model"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(None, description="Analysis ID")
    analysis_date: Optional[datetime] = Field(None, description="Analysis execution date")
    predicted_crash_date: Optional[date] = Field(None, description="Predicted crash date")
    predicted_critical_time: Optional[date] = Field(None, description="Predicted critical time")
    days_to_crash: Optional[int] = Field(None, description="Days to predicted crash")
    confidence_interval: Optional[str] = Field(None, description="Confidence interval")
    r_squared: Optional[float] = Field(None, description="R-squared value")

    # Make these optional since they don't exist in the current DB
    created_at: Optional[datetime] = Field(None, description="Record creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")


class FCOAnalysisList(BaseModel):
    """List of FCO analyses"""
    total: int = Field(..., description="Total number of records")
    items: List[FCOAnalysisResponse] = Field(..., description="List of analyses")
    page: int = Field(default=1, description="Current page")
    per_page: int = Field(default=50, description="Items per page")


class FCOSymbolSummary(BaseModel):
    """Summary for a specific symbol"""
    symbol: str
    latest_confidence: float
    latest_bubble_type: str
    latest_predicted_tc: Optional[float]
    total_analyses: int
    last_analysis_date: date
    trend: Literal["increasing", "decreasing", "stable"]


class FCOTimeSeriesData(BaseModel):
    """Time series data for charts"""
    dates: List[date]
    confidences: List[float]  # Changed to match actual usage
    confidence_neg_values: Optional[List[float]] = None
    trust_values: Optional[List[float]] = None  # Make optional
    predicted_tc_values: Optional[List[Optional[float]]] = None


class FCOHistoricalQuery(BaseModel):
    """Query parameters for historical data"""
    symbol: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    bubble_type: Optional[Literal["positive", "negative", "none", "all"]] = "all"
    limit: int = Field(default=1000, le=10000)
    order_by: Literal["date_asc", "date_desc", "confidence_desc"] = "date_desc"


class FCOTimeSeriesWithPrice(BaseModel):
    """Time series data with price and LPPL fit for visualization"""
    dates: List[str]
    prices: List[float]  # Original price data
    log_prices: List[float]  # Log-transformed prices for LPPL fitting
    lppl_fit: Optional[List[float]] = None  # LPPL fitted values (in log scale)
    confidence: float  # DS-LPPLS Confidence for this analysis
    trust: Optional[float] = None  # DS-LPPLS Trust (optional)
    predicted_crash_date: str  # Predicted crash date
    analysis_basis_date: str  # Analysis basis date
    fitting_window_start_date: Optional[str] = None  # Start date of fitting window
    fitting_window_days: Optional[int] = None  # Number of days in fitting window
    symbol: str
    bubble_type: str  # 'positive' or 'negative'
    # LPPL parameters for reconstruction if needed
    lppl_params: Optional[Dict[str, float]] = None
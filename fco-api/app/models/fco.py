"""
FCO Analysis Pydantic Models
"""

from datetime import date, datetime
from typing import Optional, List, Literal
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
    ds_lppls_confidence: float = Field(..., ge=0, le=1, description="DS-LPPLS Confidence (0-1)")
    ds_lppls_confidence_neg: float = Field(..., ge=0, le=1, description="DS-LPPLS Confidence Negative")
    ds_lppls_trust: float = Field(..., ge=0, le=1, description="DS-LPPLS Trust indicator")
    bubble_type: Literal["positive", "negative", "none"] = Field(..., description="Detected bubble type")


class ClusteringResult(BaseModel):
    """Clustering analysis result"""
    predicted_tc: float = Field(..., description="Predicted critical time (days)")
    tc_std: float = Field(..., description="Standard deviation of tc")
    scenario_probability: float = Field(..., ge=0, le=1, description="Scenario probability")
    cluster_method: str = Field(default="dbscan", description="Clustering method used")


class MultiWindowInfo(BaseModel):
    """Multi-window analysis information"""
    num_windows: int = Field(..., description="Number of time windows analyzed")
    num_qualified_fits: int = Field(..., description="Number of qualified fits")
    window_min: int = Field(..., description="Minimum window size")
    window_max: int = Field(..., description="Maximum window size")
    window_step: int = Field(..., description="Window step size")


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
    
    id: int = Field(..., description="Analysis ID")
    analysis_date: datetime = Field(..., description="Analysis execution date")
    predicted_crash_date: Optional[date] = Field(None, description="Predicted crash date")
    days_to_crash: Optional[int] = Field(None, description="Days to predicted crash")
    confidence_interval: Optional[str] = Field(None, description="Confidence interval")
    
    created_at: datetime = Field(..., description="Record creation time")
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
    confidence_values: List[float]
    confidence_neg_values: List[float]
    trust_values: List[float]
    predicted_tc_values: List[Optional[float]]


class FCOHistoricalQuery(BaseModel):
    """Query parameters for historical data"""
    symbol: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    bubble_type: Optional[Literal["positive", "negative", "none", "all"]] = "all"
    limit: int = Field(default=1000, le=10000)
    order_by: Literal["date_asc", "date_desc", "confidence_desc"] = "date_desc"
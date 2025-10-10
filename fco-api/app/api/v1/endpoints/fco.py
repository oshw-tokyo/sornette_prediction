"""
FCO Analysis API Endpoints
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.models.fco import (
    FCOAnalysisResponse,
    FCOAnalysisList,
    FCOSymbolSummary,
    FCOTimeSeriesData,
    FCOHistoricalQuery,
    FCOTimeSeriesWithPrice
)
from app.services.fco_service import FCOService

router = APIRouter(prefix="/fco", tags=["FCO Analysis"])


@router.get("/symbols", response_model=List[dict])
async def get_available_symbols():
    """Get list of available symbols with FCO analysis"""
    service = FCOService()
    return service.get_available_symbols()


@router.get("/analysis/{symbol}/latest", response_model=FCOAnalysisResponse)
async def get_latest_analysis(symbol: str):
    """Get latest FCO analysis for a symbol"""
    service = FCOService()
    analysis = service.get_latest_analysis(symbol)
    
    if not analysis:
        raise HTTPException(status_code=404, detail=f"No analysis found for {symbol}")
    
    return analysis


@router.get("/analysis/{symbol}/history", response_model=List[FCOAnalysisResponse])
async def get_historical_analyses(
    symbol: str,
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    limit: int = Query(100, le=1000, description="Maximum number of results")
):
    """Get historical FCO analyses for a symbol"""
    service = FCOService()
    analyses = service.get_historical_analyses(symbol, start_date, end_date, limit)
    
    if not analyses:
        raise HTTPException(status_code=404, detail=f"No analyses found for {symbol}")
    
    return analyses


@router.get("/analysis/{symbol}/summary", response_model=FCOSymbolSummary)
async def get_symbol_summary(symbol: str):
    """Get summary statistics for a symbol"""
    service = FCOService()
    summary = service.get_symbol_summary(symbol)
    
    if not summary:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    
    return summary


@router.get("/analysis/{symbol}/timeseries", response_model=FCOTimeSeriesData)
async def get_time_series_data(
    symbol: str,
    start_date: Optional[date] = Query(None, description="Start date for time series"),
    end_date: Optional[date] = Query(None, description="End date for time series")
):
    """Get time series data for visualization"""
    service = FCOService()
    data = service.get_time_series_data(symbol, start_date, end_date)

    if not data or not data.get('dates'):
        raise HTTPException(status_code=404, detail=f"No time series data found for {symbol}")

    # Convert dict to FCOTimeSeriesData
    return FCOTimeSeriesData(
        dates=data.get('dates', []),
        confidences=data.get('confidences', []),
        confidence_neg_values=data.get('confidence_neg_values'),
        predicted_tc_values=data.get('predicted_tc_values')
    )


@router.get("/analysis/{symbol}/price-series/{analysis_id}", response_model=FCOTimeSeriesWithPrice)
async def get_price_series_with_lppl(
    symbol: str,
    analysis_id: int,
    days_before: int = Query(365, description="Days of price data before analysis date")
):
    """Get price data with LPPL fit for a specific analysis"""
    service = FCOService()
    data = service.get_price_series_with_lppl(symbol, analysis_id, days_before)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for {symbol} analysis {analysis_id}"
        )

    # Convert dict to FCOTimeSeriesWithPrice if needed
    if isinstance(data, dict):
        return FCOTimeSeriesWithPrice(
            dates=data.get('dates', []),
            prices=data.get('prices', []),
            log_prices=data.get('log_prices', []),
            lppl_fit=data.get('lppl_fit'),
            confidence=data.get('confidence', 0.0),
            trust=data.get('trust'),
            predicted_crash_date=data.get('predicted_crash_date', ''),
            analysis_basis_date=data.get('analysis_basis_date', ''),
            symbol=data.get('symbol', symbol),
            bubble_type=data.get('bubble_type', 'positive'),
            lppl_params=data.get('lppl_params')
        )
    return data


@router.get("/analysis/all", response_model=List[dict])
async def get_all_analyses(
    limit: int = Query(1000, le=10000, description="Maximum number of results")
):
    """Get all FCO analyses for all symbols (for visualization)"""
    service = FCOService()
    analyses = service.get_all_analyses(limit)

    if not analyses:
        return []  # Return empty list instead of 404 for no data

    return analyses


@router.post("/analysis/{symbol}/run")
async def run_new_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
    period: int = Query(365, description="Analysis period in days"),
    force: bool = Query(False, description="Force new analysis even if recent exists")
):
    """Run new FCO analysis for a symbol"""
    service = FCOService()
    
    try:
        # Run analysis (can be moved to background task for long operations)
        result = service.run_new_analysis(symbol, period, force)
        return {
            "status": "success",
            "message": f"Analysis completed for {symbol}",
            "analysis_id": result.get('id')
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: int):
    """Delete an analysis by ID"""
    service = FCOService()
    
    if service.delete_analysis(analysis_id):
        return {"status": "success", "message": f"Analysis {analysis_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")


@router.get("/confidence-threshold")
async def get_confidence_threshold():
    """Get current confidence threshold settings"""
    return {
        "bubble_threshold": 0.3,
        "high_confidence": 0.5,
        "critical_confidence": 0.7,
        "description": "DS-LPPLS Confidence thresholds for bubble detection"
    }
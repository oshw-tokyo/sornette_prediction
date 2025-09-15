"""
FastAPI Main Application
FCO Analysis System v2.1
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.fco_service import FCOService

# Initialize templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use settings.BACKEND_CORS_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs": "/docs",
        "api": settings.API_V1_STR
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard HTML template"""
    service = FCOService()
    try:
        symbols = service.get_available_symbols()
    except Exception as e:
        symbols = []
        print(f"Error fetching symbols: {e}")
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "symbols": symbols
        }
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info"
    )
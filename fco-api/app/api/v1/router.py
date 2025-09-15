"""
API v1 Router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import fco

api_router = APIRouter()

# Include FCO endpoints
api_router.include_router(fco.router)

# Future endpoints can be added here:
# api_router.include_router(lppl.router)
# api_router.include_router(auth.router)
# api_router.include_router(market_data.router)
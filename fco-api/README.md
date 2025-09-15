# FCO Analysis API (FastAPI Backend)

## Overview

FastAPI backend for FCO v2.1 system, providing REST API endpoints for FCO analysis data.

## Features

- ✅ REST API for FCO analysis data
- ✅ Reuses existing Python FCO engine
- ✅ Auto-generated OpenAPI documentation
- ✅ Type validation with Pydantic
- ✅ CORS support for React frontend
- ✅ WebSocket support (ready for real-time updates)

## Quick Start

### 1. Install Dependencies

```bash
cd fco-api
pip install -r requirements.txt
```

### 2. Run Development Server

```bash
# From fco-api directory
python app/main.py

# Or use uvicorn directly
uvicorn app.main:app --reload --port 8000
```

### 3. Access API

- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- API Base URL: http://localhost:8000/api/v1

## API Endpoints

### FCO Analysis

- `GET /api/v1/fco/symbols` - Get available symbols
- `GET /api/v1/fco/analysis/{symbol}/latest` - Get latest analysis
- `GET /api/v1/fco/analysis/{symbol}/history` - Get historical analyses
- `GET /api/v1/fco/analysis/{symbol}/summary` - Get symbol summary
- `GET /api/v1/fco/analysis/{symbol}/timeseries` - Get time series data
- `POST /api/v1/fco/analysis/{symbol}/run` - Run new analysis
- `DELETE /api/v1/fco/analysis/{analysis_id}` - Delete analysis

## Project Structure

```
fco-api/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API endpoints
│   │       └── router.py       # API router
│   ├── core/
│   │   └── config.py          # Configuration
│   ├── models/
│   │   └── fco.py             # Pydantic models
│   ├── services/
│   │   └── fco_service.py     # Business logic
│   └── db/
│       ├── base.py            # Database config
│       └── session.py         # Session management
├── requirements.txt
└── README.md
```

## Configuration

The API uses environment variables from the project root `.env` file:

```env
FRED_API_KEY=your_fred_api_key
ALPHA_VANTAGE_KEY=your_alpha_vantage_key
COINGECKO_API_KEY=your_coingecko_api_key
SECRET_KEY=your_secret_key_for_jwt
```

## Development

### Run with auto-reload

```bash
uvicorn app.main:app --reload --port 8000
```

### Test API

```bash
# Get available symbols
curl http://localhost:8000/api/v1/fco/symbols

# Get latest analysis for SP500
curl http://localhost:8000/api/v1/fco/analysis/SP500/latest

# Get time series data
curl http://localhost:8000/api/v1/fco/analysis/SP500/timeseries
```

## Production Deployment

For production deployment on Railway:

1. Set environment variables in Railway dashboard
2. Configure PostgreSQL database
3. Update `DATABASE_URL` environment variable
4. Deploy using Railway CLI or GitHub integration

## Next Steps

- [ ] Add authentication endpoints
- [ ] Implement WebSocket for real-time updates
- [ ] Add LPPL analysis endpoints
- [ ] Add market data endpoints
- [ ] Implement rate limiting
- [ ] Add comprehensive tests
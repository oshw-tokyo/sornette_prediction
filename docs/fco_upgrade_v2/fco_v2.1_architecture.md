# FCO v2.1 System Architecture - React + FastAPI

## 🎯 Architecture Overview

FCO v2.1は、商用SaaS提供を目的とした、スケーラブルなWebアプリケーションアーキテクチャです。

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer (Browser)                   │
├─────────────────────────────────────────────────────────────┤
│  React App (Next.js)                                        │
│  ├── TypeScript                                             │
│  ├── Tailwind CSS                                           │
│  ├── Plotly.js (Square Aspect Ratio Charts)                │
│  └── TanStack Query (Data Fetching)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/WSS
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                         │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server                                             │
│  ├── REST Endpoints                                         │
│  ├── WebSocket Support                                      │
│  ├── JWT Authentication                                     │
│  └── CORS Management                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Python Core (既存実装の再利用)                              │
│  ├── core/fitting/fco_engine.py                            │
│  ├── core/fco_indicators/                                  │
│  ├── applications/analysis_tools/                          │
│  └── infrastructure/market_data/                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
├─────────────────────────────────────────────────────────────┤
│  Databases                                                  │
│  ├── PostgreSQL (Production)                                │
│  ├── SQLite (Development)                                   │
│  └── Redis (Cache/Session)                                  │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

### Frontend (React/Next.js)

```
fco-dashboard-frontend/
├── pages/                      # Next.js Pages Router (枯れた技術優先)
│   ├── _app.tsx               # App wrapper
│   ├── _document.tsx          # HTML document
│   ├── index.tsx              # Home page
│   ├── dashboard/
│   │   └── index.tsx          # Dashboard main
│   └── api/                   # API routes (if needed)
│       └── auth/
├── components/
│   ├── ui/                    # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── [other shadcn components]
│   ├── charts/
│   │   ├── FCOScatterPlot.tsx      # Plotly.js - Square aspect ratio
│   │   ├── FCOClusteringPlot.tsx   # Plotly.js - Square aspect ratio
│   │   └── [Future charts]          # Recharts for time-series
│   ├── filters/
│   │   ├── DateRangePicker.tsx
│   │   ├── SymbolSelector.tsx
│   │   └── QualityFilter.tsx
│   └── layout/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Footer.tsx
├── hooks/
│   ├── useFCOData.ts
│   ├── useWebSocket.ts
│   └── useAuth.ts
├── lib/
│   ├── api-client.ts
│   ├── websocket-client.ts
│   ├── chart-config.ts
│   └── utils.ts               # Utility functions
├── types/
│   ├── fco.ts
│   ├── lppl.ts
│   └── api.ts
└── styles/
    └── globals.css            # Tailwind CSS
```

### Backend (FastAPI)

```
fco-api/
├── app/
│   ├── main.py                # FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── fco.py
│   │   │   │   ├── lppl.py
│   │   │   │   ├── auth.py
│   │   │   │   └── market_data.py
│   │   │   └── router.py
│   │   └── websocket/
│   │       └── realtime.py
│   ├── core/
│   │   ├── config.py          # Settings
│   │   ├── security.py        # JWT, Auth
│   │   └── dependencies.py    # DI
│   ├── models/
│   │   ├── fco.py            # Pydantic models
│   │   ├── lppl.py
│   │   └── user.py
│   ├── services/
│   │   ├── fco_service.py    # Business logic
│   │   ├── lppl_service.py
│   │   └── market_service.py
│   └── db/
│       ├── base.py
│       ├── session.py
│       └── repositories/
│           ├── fco_repo.py
│           └── lppl_repo.py
├── migrations/                 # Alembic
├── tests/
└── requirements.txt
```

## 🔄 Data Flow

### 1. ユーザーリクエストフロー
```
User Action → React Component → API Call → FastAPI Endpoint 
    → Service Layer → Repository → Database → Response
```

### 2. リアルタイム更新フロー
```
Market Data Update → WebSocket Server → Connected Clients
    → React Component Update → UI Re-render
```

### 3. 認証フロー
```
Login → Auth0/Clerk → JWT Token → Store in HttpOnly Cookie
    → Include in API Requests → Validate in FastAPI Middleware
```

## 🔐 Security Architecture

### Frontend Security
- Content Security Policy (CSP)
- XSS Protection
- HTTPS Only
- Secure Cookie Storage

### API Security
- JWT Bearer Token Authentication
- Rate Limiting (per user/IP)
- Input Validation (Pydantic)
- SQL Injection Prevention (ORM)

### Data Security
- Encryption at Rest (Database)
- Encryption in Transit (TLS)
- PII Masking
- Audit Logging

## 🚀 Deployment Architecture

### Development Environment
```yaml
services:
  frontend:
    platform: Node.js 20
    port: 3000
    hot-reload: true
    
  backend:
    platform: Python 3.11
    port: 8000
    auto-reload: true
    
  database:
    platform: SQLite
    file: ./dev.db
```

### Production Environment
```yaml
services:
  frontend:
    platform: Vercel
    regions: [global]
    cdn: true
    
  backend:
    platform: Railway
    instances: 2-10 (auto-scale)
    memory: 512MB-2GB
    
  database:
    platform: PostgreSQL
    size: 1GB-10GB
    backup: daily
    
  cache:
    platform: Redis
    memory: 256MB
```

## 📊 Performance Targets

### Frontend Performance
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Lighthouse Score: > 90

### API Performance
- Response Time: < 200ms (p95)
- Throughput: > 1000 req/s
- WebSocket Latency: < 50ms

### Database Performance
- Query Time: < 50ms (p95)
- Connection Pool: 20-100
- Cache Hit Rate: > 80%

## 🔄 Migration Strategy

### Phase 1: Parallel Development
- v2.0 (Streamlit) remains operational
- v2.1 (React+FastAPI) developed in parallel
- Shared database (read-only for v2.1 initially)

### Phase 2: Feature Parity
- Implement all v2.0 features in v2.1
- A/B testing with select users
- Performance comparison

### Phase 3: Gradual Migration
- Route new users to v2.1
- Migrate existing users in batches
- Monitor and rollback capability

### Phase 4: Deprecation
- v2.0 enters maintenance mode
- Final data migration
- v2.0 shutdown

## 🎯 Key Design Decisions

### Why React + Next.js?
1. **SEO Optimization**: Server-side rendering for public pages
2. **Performance**: Automatic code splitting and optimization
3. **Developer Experience**: Hot reload, TypeScript support
4. **Ecosystem**: Vast library ecosystem

### Why FastAPI?
1. **Performance**: One of the fastest Python frameworks
2. **Developer Experience**: Auto-generated OpenAPI docs
3. **Type Safety**: Pydantic validation
4. **Async Support**: Native async/await

### Why This Architecture?
1. **Separation of Concerns**: Clear frontend/backend separation
2. **Scalability**: Independent scaling of components
3. **Maintainability**: Modular, testable code
4. **Reusability**: Existing Python logic preserved

## 📈 Monitoring & Observability

### Application Monitoring
- Sentry (Error tracking)
- Vercel Analytics (Frontend metrics)
- Railway Metrics (Backend metrics)

### Business Metrics
- User engagement tracking
- API usage statistics
- Performance dashboards

### Alerting
- Error rate thresholds
- Performance degradation
- Security incidents

## 🔧 Implementation Status (2025-01-15)

### ✅ Completed Components

#### Backend (FastAPI)
- **API Structure**: Full RESTful API implementation
- **Database Integration**: SQLite with relative path resolution
- **Service Layer**: FCOService wrapping existing Python logic
- **Data Models**: Pydantic models for type validation
- **Endpoints**: All core FCO analysis endpoints operational

#### Frontend (React/Next.js)
- **Project Setup**: Next.js 14 with Pages Router
- **UI Components**: Basic layout and symbol selector
- **API Client**: Axios-based client with TypeScript
- **Styling**: Tailwind CSS with dark theme
- **Type Definitions**: Complete TypeScript interfaces

### 🚧 In Progress

#### Frontend Development
- **Chart Components**: Implementing Recharts for data visualization
- **Real-time Updates**: WebSocket integration for live data
- **Advanced Filters**: Date range and quality filters
- **Responsive Design**: Mobile-first approach

#### Backend Enhancement
- **Authentication**: JWT implementation pending
- **Caching Layer**: Redis integration planned
- **Background Tasks**: Celery for long-running analyses

### 📋 Pending Implementation

1. **Production Infrastructure**
   - Docker containerization
   - CI/CD pipeline setup
   - Environment configuration
   - SSL/TLS certificates

2. **Advanced Features**
   - Export functionality (CSV/PDF)
   - Email notifications
   - User preferences storage
   - Multi-language support

3. **Performance Optimization**
   - Database query optimization
   - Frontend code splitting
   - Image optimization
   - API response caching

## 🐛 Issues Resolved

### Symbol Name Display Issue
**Problem**: API returning string arrays instead of objects
**Solution**: Modified `get_available_symbols()` to return `{symbol, name}` objects
```python
return [
    {'symbol': symbol[0], 'name': symbol_map.get(symbol[0], symbol[0])}
    for symbol in symbols
]
```

### Path Resolution Issue
**Problem**: Hardcoded absolute paths breaking portability
**Solution**: Implemented relative path resolution using pathlib
```python
from pathlib import Path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
db_path = project_root / "results" / "fco_analysis_results.db"
```

### Module Resolution Error
**Problem**: Next.js couldn't resolve `@/styles/globals.css`
**Solution**: Ensured proper file structure and tsconfig paths

### Port Conflict
**Problem**: Port 3000 was occupied
**Solution**: Configured Next.js to use port 3001

## 📚 Lessons Learned

1. **Path Management**: Always use pathlib for cross-platform compatibility
2. **API Design**: Return consistent object structures, not primitive arrays
3. **Type Safety**: Leverage TypeScript to catch errors early
4. **Error Messages**: Provide clear, actionable error messages
5. **Documentation**: Keep architecture docs in sync with implementation

## 🎯 Next Implementation Steps

### Immediate Priority (Week 1)
1. Complete chart components with real data
2. Implement WebSocket for real-time updates
3. Add loading states and error boundaries
4. Create comprehensive test suite

### Short Term (Week 2-3)
1. Authentication system implementation
2. User preference storage
3. Export functionality
4. Mobile responsive design

### Medium Term (Month 1-2)
1. Production deployment setup
2. Performance optimization
3. Monitoring and alerting
4. Documentation and training materials

---

**Document Version**: 1.1
**Last Updated**: 2025-01-15
**Status**: Active Architecture for v2.1 - Implementation in Progress
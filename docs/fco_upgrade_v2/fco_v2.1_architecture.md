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
│  ├── Recharts/Plotly.js                                     │
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
├── app/                        # Next.js App Router
│   ├── layout.tsx             # Root layout
│   ├── page.tsx               # Home page
│   ├── dashboard/
│   │   ├── page.tsx           # Dashboard main
│   │   └── [symbol]/
│   │       └── page.tsx       # Symbol detail
│   └── api/                   # API routes (BFF pattern)
│       └── auth/
├── components/
│   ├── ui/                    # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── [other shadcn components]
│   ├── charts/
│   │   ├── FCOConfidenceChart.tsx  # Recharts
│   │   ├── LPPLPredictionChart.tsx  # Plotly.js
│   │   └── ClusteringAnalysis.tsx   # Recharts + API
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

---

**Document Version**: 1.0
**Created**: 2025-09-14
**Status**: Active Architecture for v2.1
# FCO v2.1 Migration Plan: Streamlit → React + FastAPI

## 📊 Executive Summary

FCO v2.0のStreamlit実装からReact+FastAPIへの技術スタック移行計画。
商用SaaS化に向けたスケーラビリティと開発効率の向上を目的とする。

## 🎯 Migration Objectives

1. **パフォーマンス向上**: クライアントサイドレンダリングによる10倍高速化
2. **開発効率**: 生成AI（Claude Code）との親和性向上
3. **商用対応**: 認証・課金システムの統合容易性
4. **スケーラビリティ**: 水平スケーリング対応アーキテクチャ

## 📋 Impact Analysis

### 影響を受けるドキュメント（12件）

#### 高優先度（直接更新必要）
1. `docs/fco_dashboard_implementation_summary.md` - 実装サマリー
2. `docs/fco_dashboard_requirements.md` - 要件定義
3. `docs/dashboard_requirements.md` - ダッシュボード要件
4. `docs/dashboard_implementation_specification.md` - 実装仕様

#### 中優先度（参照更新必要）
5. `docs/progress_management/CURRENT_PROGRESS.md` - 進捗管理
6. `docs/progress_management/CURRENT_ISSUES.md` - 課題管理
7. `docs/fco_upgrade_v2/full_historical_data_operation_guide.md` - 運用ガイド

#### 低優先度（参考情報更新）
8. `docs/service_commercialization/implementation_gap_analysis.md`
9. `docs/service_commercialization/lppl_service_specification_simplified.md`
10. `docs/service_commercialization/lppl_service_specification_v2.md`
11. `docs/progress_management/CURRENT_ISSUES_ARCHIVE.md`
12. `docs/implementation/Data_Accumulation_and_UX_Strategy.md`

### 影響を受ける実装ファイル

#### 削除/置換対象（Streamlit依存）
1. `infrastructure/visualization/fco_dashboard_components.py` → React Components
2. `applications/dashboards/main_dashboard.py` → React App
3. `applications/dashboards/dashboard_launcher.py` → Next.js Server

#### 修正対象（API化）
4. `entry_points/main.py` - FastAPIサーバー起動追加
5. `core/fitting/fco_engine.py` - API エンドポイント対応

#### 保持（バックエンド再利用）
- `infrastructure/database/fco_results_database.py` - そのまま利用
- `core/fco_indicators/` - APIから呼び出し
- `infrastructure/market_data/` - データ取得層として維持

## 🏗️ Architecture Design

### 現在のアーキテクチャ（v2.0）
```
User → Streamlit Server → Python Backend → SQLite DB
         (全処理サーバー側)
```

### 新アーキテクチャ（v2.1）
```
User → React App → FastAPI → Python Backend → PostgreSQL
      (Browser)    (REST)     (既存ロジック)   (Production DB)
```

## 📅 Implementation Phases

### Phase 1: FastAPI Backend（Week 1）
- [ ] FastAPI プロジェクト構造作成
- [ ] 既存Pythonロジックのラッピング
- [ ] REST APIエンドポイント設計
- [ ] CORS設定とセキュリティ

### Phase 2: React Frontend Setup（Week 2）
- [ ] Next.js プロジェクト初期化
- [ ] TypeScript設定
- [ ] Tailwind CSS統合
- [ ] 基本レイアウト実装

### Phase 3: Data Visualization（Week 3）
- [ ] Recharts/Plotly.js統合
- [ ] FCO Confidence チャート
- [ ] リアルタイムデータ更新
- [ ] フィルタリング機能

### Phase 4: Authentication & Deployment（Week 4）
- [ ] Auth0/Clerk統合
- [ ] Vercel デプロイ設定
- [ ] Railway バックエンド設定
- [ ] 環境変数管理

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts + Plotly.js
- **State**: Zustand / TanStack Query
- **Hosting**: Vercel

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL (Production) / SQLite (Dev)
- **ORM**: SQLAlchemy
- **Hosting**: Railway

### DevOps
- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry
- **Analytics**: Vercel Analytics

## 💰 Cost Analysis

### 開発環境（無料）
- Vercel Free Tier: $0
- Railway Hobby: $5/月
- PostgreSQL: 含む

### 本番環境（推定）
- Vercel Pro: $20/月
- Railway Team: $20/月
- Total: ~$40/月（100ユーザー規模）

## ⚠️ Risk Mitigation

### リスク1: データ移行
- **対策**: SQLite → PostgreSQL マイグレーションスクリプト
- **バックアップ**: v2.0ブランチ維持

### リスク2: 機能欠落
- **対策**: 段階的移行、機能パリティチェックリスト
- **テスト**: E2Eテスト自動化

### リスク3: 学習曲線
- **対策**: React/TypeScriptボイラープレート準備
- **支援**: Claude Codeによるコード生成

## ✅ Success Criteria

1. **パフォーマンス**: 初期ロード3秒以内
2. **機能完全性**: v2.0の全機能実装
3. **開発効率**: 新機能追加時間50%削減
4. **ユーザー体験**: リアルタイムフィルタリング実現

## 📝 Next Steps

1. このドキュメントのレビューと承認
2. FastAPIプロジェクト構造の作成
3. 最初のAPIエンドポイント実装
4. React プロジェクトのセットアップ

---

**Document Version**: 1.0
**Created**: 2025-09-14
**Author**: Claude Code
**Status**: Draft
# Dashboard ドキュメント

**最終更新**: 2025-10-09
**重要**: このプロジェクトには**2つの異なるダッシュボードシステム**が存在します

---

## 🎯 2つの並行稼働ダッシュボード

| 項目 | LPPL Dashboard | FCO Dashboard |
|------|---------------|--------------|
| **技術スタック** | Streamlit | React + FastAPI |
| **実装状況** | ✅ 完成・稼働中 | 🔄 Phase 2進行中 |
| **対象分析** | LPPL分析 (単一窓) | FCO分析 (126窓) |
| **実装ファイル** | `applications/dashboards/main_dashboard.py` | `fco-api/`, `fco-dashboard-frontend/` |
| **起動コマンド** | `python entry_points/main.py dashboard` | `uvicorn app.main:app` + `npm run dev` |

---

## 📚 LPPL Dashboard (Streamlit) - 現行稼働中システム

### 現行文書

#### 1. [dashboard_requirements.md](../dashboard_requirements.md)
**ダッシュボード要件定義書 - 安定版v1.0対応**
- **技術スタック**: Streamlit
- **対象**: Symbol Analysis Dashboard (main_dashboard.py)
- **バージョン**: v1.1-stable (Symbol Filters Architecture v2)
- **作成日**: 2025-08-10 (最終更新: 2025-08-11)
- **状態**: ✅ 現行稼働中

**主要機能**:
- Symbol Filters Architecture v2
- Crash Prediction Clustering Analytics
- LPPL Fitting Analysis
- Prediction Convergence
- Parameter Details

#### 2. [dashboard_implementation_specification.md](../dashboard_implementation_specification.md)
**ダッシュボード実装仕様書（実装状況ベース）**
- **技術スタック**: Streamlit
- **対象**: applications/dashboards/main_dashboard.py
- **バージョン**: v1.4 (Dashboard UI Major Improvements)
- **作成日**: 2025-08-13
- **状態**: ✅ 現行稼働中

**実装詳細**:
- 4タブ構成システム
- Symbol Filters実装
- データベース統合
- セッション状態管理

### 起動方法

```bash
# LPPL Dashboard起動
python entry_points/main.py dashboard
```

**アクセス**: http://localhost:8501

---

## 🚀 FCO Dashboard (React + FastAPI) - 開発中システム

### 実装状況

**Phase 1**: ✅ FastAPIバックエンド実装完了
**Phase 2**: 🔄 Reactフロントエンド実装中
**Phase 3**: 📋 データ可視化コンポーネント計画中
**Phase 4**: 📋 認証・デプロイメント計画中

### プロジェクト構成

#### Frontend: Next.js + React + TypeScript

**プロジェクトディレクトリ**: `fco-dashboard-frontend/`

```
fco-dashboard-frontend/
├── pages/
│   ├── index.tsx                    # メインページ
│   └── _app.tsx                     # アプリケーションルート
├── components/
│   ├── charts/
│   │   └── FCOTimeSeriesChart.tsx   # 時系列チャート
│   └── containers/
│       └── FCOAnalysisContainer.tsx # 分析コンテナ
├── types/
│   └── fco.ts                       # FCO型定義
└── styles/
    └── globals.css                  # グローバルスタイル
```

#### Backend: FastAPI + SQLite

**プロジェクトディレクトリ**: `fco-api/`

```
fco-api/
├── app/
│   ├── main.py                      # FastAPIアプリケーション
│   ├── api/v1/endpoints/
│   │   └── fco.py                   # FCOエンドポイント
│   ├── models/
│   │   └── fco.py                   # FCOモデル
│   └── services/
│       └── fco_service.py           # FCOビジネスロジック
└── requirements.txt
```

### 起動方法

```bash
# Backend起動
cd fco-api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend起動
cd fco-dashboard-frontend
npm run dev
```

**アクセス**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### 関連文書

#### アーキテクチャ関連
- [../fco_upgrade_v2/v2.1_webapp/fco_v2.1_architecture.md](../fco_upgrade_v2/v2.1_webapp/fco_v2.1_architecture.md) - FCO v2.1 完全アーキテクチャ
- [../fco_upgrade_v2/v2.1_webapp/implementation_plan_v2.1_next_steps.md](../fco_upgrade_v2/v2.1_webapp/implementation_plan_v2.1_next_steps.md) - 次期実装計画

#### 実装戦略
- [../fco_upgrade_v2/v2.1_webapp/frontend_implementation_strategy.md](../fco_upgrade_v2/v2.1_webapp/frontend_implementation_strategy.md) - React実装戦略
- [../fco_upgrade_v2/v2.1_webapp/price_data_storage_plan.md](../fco_upgrade_v2/v2.1_webapp/price_data_storage_plan.md) - 価格データ保存計画

#### 技術仕様
- [../fco_upgrade_v2/foundation/technical_implementation_plan.md](../fco_upgrade_v2/foundation/technical_implementation_plan.md) - 技術実装詳細計画
- [../fco_upgrade_v2/foundation/full_window_storage_strategy.md](../fco_upgrade_v2/foundation/full_window_storage_strategy.md) - 全窓保存戦略

---

## 🗂️ アーカイブ文書 (Streamlit版 FCO Dashboard)

以下の文書は **FCO Dashboard (Streamlit版)** の開発文書で、React+FastAPI移行により廃止されました。

**アーカイブ場所**: [../progress_management/archives/deprecated_streamlit/](../progress_management/archives/deprecated_streamlit/)

### 廃止された文書

1. **fco_dashboard_requirements.md** (2025-09-14)
   - Streamlit版 FCO Dashboard 要件定義書
   - → React版に置き換え済み

2. **fco_dashboard_implementation_summary.md** (2025-09-14)
   - Streamlit版 FCO Dashboard 実装概要
   - → React版に置き換え済み

3. **migration_to_react_fastapi.md** (2025-09-15)
   - Streamlit → React + FastAPI 移行記録
   - → 移行完了、参考資料化

**参照**: [../progress_management/archives/deprecated_streamlit/README.md](../progress_management/archives/deprecated_streamlit/README.md)

**重要**: これらは **FCO Dashboard** のStreamlit版であり、現在稼働中の **LPPL Dashboard (Streamlit)** とは**別システム**です。

---

## 🔄 主要機能比較

### LPPL Dashboard (Streamlit) - 現行稼働中

1. **銘柄フィルタリング**
   - Symbol Filters Architecture v2
   - カテゴリ別・データソース別フィルター
   - Apply Button制御

2. **LPPL分析表示**
   - 単一窓（365日固定）分析
   - R²品質評価
   - 予測クラッシュ日・価格

3. **Crash Prediction Clustering**
   - 1D DBSCAN クラスタリング
   - R²重み付き平均
   - 投資判断支援テーブル

4. **時系列可視化**
   - Streamlit/Plotly統合
   - インタラクティブプロット
   - 日付範囲フィルタリング

### FCO Dashboard (React+FastAPI) - 開発中

1. **全126窓分析表示** (Phase 3計画中)
   - DS-LPPLS Confidence/Trust指標
   - R²分布ヒストグラム
   - tc予測scatter plot

2. **高度な可視化** (Phase 3計画中)
   - Viridisカラーグラディエント
   - React + Plotly.js統合
   - レスポンシブデザイン

3. **認証システム** (Phase 4計画中)
   - ユーザー管理
   - セッション管理
   - アクセス制御

詳細: [../fco_upgrade_v2/foundation/full_window_implementation_roadmap.md](../fco_upgrade_v2/foundation/full_window_implementation_roadmap.md)

---

## 📖 関連ドキュメント

### プロジェクト全体
- [../README.md](../README.md) - ドキュメント全体索引
- [../fco_upgrade_v2/README.md](../fco_upgrade_v2/README.md) - FCO v2.1/v3アップグレード概要

### 進捗管理
- [../progress_management/CURRENT_PROGRESS.md](../progress_management/CURRENT_PROGRESS.md) - 現在の進捗状況
- [../progress_management/CURRENT_ISSUES.md](../progress_management/CURRENT_ISSUES.md) - アクティブな課題

---

**管理**: プロジェクトオーナー + Claude Code
**最終更新**: 2025-10-09
**修正内容**: Streamlit/Reactの正確な区別を明記

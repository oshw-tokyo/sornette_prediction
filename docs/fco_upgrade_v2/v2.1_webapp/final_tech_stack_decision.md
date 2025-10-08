# FCO v2.1 最終技術スタック決定書

## 📊 決定日: 2025-09-14

## ✅ 採用技術スタック

### Frontend
| レイヤー | 技術選択 | 理由 |
|---------|----------|------|
| Framework | **Next.js 14 + React 18** | Claude Code最適化、SSR/SSG対応、SEO対応 |
| CSS Framework | **Tailwind CSS** | 開発効率、カスタマイズ性、Claude Code親和性 |
| UI Components | **shadcn/ui** | コピー型実装、依存性最小、高品質コンポーネント |
| Charts (Basic) | **Recharts** | 簡単実装、React親和性、基本グラフ対応 |
| Charts (Advanced) | **Plotly.js** | 高度な金融グラフ、3D対応、インタラクティブ |
| State Management | **Zustand** | 軽量、学習曲線緩やか、TypeScript対応 |
| Data Fetching | **TanStack Query** | キャッシュ管理、リトライ、最適化 |

### Backend
| レイヤー | 技術選択 | 理由 |
|---------|----------|------|
| Framework | **FastAPI** | ✅実装済み、高速、自動ドキュメント生成 |
| Database | **SQLite** (開発) / **PostgreSQL** (本番) | 既存DB活用、スケーラビリティ |
| Clustering | **scikit-learn** | 既存DBSCAN実装活用、Python統合 |
| Data Format | **Parquet + JSON API** | 高速読込、圧縮効率、API互換性 |

### Deployment
| 環境 | サービス | 理由 |
|------|----------|------|
| Frontend | **Vercel** | Next.js最適化、無料枠充実、簡単デプロイ |
| Backend (開発) | **ローカル** | 開発効率、デバッグ容易 |
| Backend (本番) | **Railway** | 簡単設定、スケーラブル、コスト効率 |

## 🔄 段階的実装計画

### Step 1: 簡易HTMLテンプレート（現在）
- **目的**: FastAPIの動作確認、データ表示テスト
- **技術**: Jinja2Templates + 基本HTML
- **期間**: 1-2時間

### Step 2: Next.js基本実装
- **目的**: React環境構築、基本レイアウト
- **技術**: Next.js + TypeScript + Tailwind CSS
- **期間**: 2-3日

### Step 3: UIコンポーネント統合
- **目的**: ユーザーインターフェース構築
- **技術**: shadcn/ui + カスタムコンポーネント
- **期間**: 2-3日

### Step 4: データ可視化
- **目的**: グラフ表示、インタラクティブ機能
- **技術**: Recharts → Plotly.js（段階的）
- **期間**: 3-4日

### Step 5: クラスタリング統合
- **目的**: 高度な分析機能
- **技術**: FastAPI + scikit-learn
- **期間**: 2-3日

## 📋 重要な設計決定

### 1. **shadcn/ui採用の理由**
- コンポーネントをコピーして使うため、バージョン依存性がない
- カスタマイズが容易
- Claude Codeが最も効率的に扱える

### 2. **Recharts → Plotly.js段階的移行**
- 基本機能はRechartsで素早く実装
- 高度な金融グラフはPlotly.jsで実装
- リスク分散と開発速度の両立

### 3. **サーバーサイドクラスタリング**
- フロントエンドの負荷軽減
- 既存Python実装の再利用
- 大規模データ（10GB）対応

### 4. **認証機能の後回し**
- MVP優先開発
- 将来的にAuth0/Clerk統合予定
- 開発段階はローカル環境で十分

## 🎯 期待される成果

1. **開発効率**: 2-3週間でMVP完成
2. **パフォーマンス**: 初期ロード3秒以内
3. **スケーラビリティ**: 10GB データ対応
4. **保守性**: コンポーネント分離設計
5. **Claude Code互換性**: 最適化されたコード生成

## ⚠️ リスクと対策

| リスク | 対策 |
|--------|------|
| 技術学習曲線 | shadcn/ui の簡単なコンポーネントから開始 |
| パフォーマンス問題 | データサンプリング、ページネーション実装 |
| セキュリティ | 開発段階はローカル限定、本番前に認証実装 |

## 📝 参考資料

- ChatGPT提案文書（2025-09-14）
- 当初のアーキテクチャ設計（fco_v2.1_architecture.md）
- Claude Code最適化ガイドライン

---

**承認**: ユーザー確認済み（2025-09-14）
**次のアクション**: 簡易HTMLテンプレート実装 → Next.jsセットアップ
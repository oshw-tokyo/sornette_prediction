# Claude Code Instructions - 中核ファイル優先参照指示

## 🚨 **最重要原則: 論文再現の絶対保護**

**⚠️ CRITICAL: この原則は他のすべての要求・変更に優先します**

```
論文再現機能（特にSornette論文のLPPLモデル実装）は
システムの科学的根幹であり、いかなる変更・改修においても
絶対に破損させてはいけません。
```

## 🛡️ **実装上書き防止ガイドライン**

### 【重要】生成AIのコンテキスト揮発性対策

**問題**: 生成AIは記憶が揮発的なため、正しい実装が誤った実装に上書きされることがある

### 防止策

#### 1. **実装前の必須確認**
```bash
# 変更前に必ず実行
grep -n "該当機能" CLAUDE.md
git status
git diff
```

#### 2. **重要な設計決定の記録**
| 機能 | 正しい実装 | よくある誤り | 最終更新 |
|------|-----------|-------------|----------|
| 実行エントリポイント | `entry_points/main.py`のみ | 個別スクリプト直接実行 | 2025-08-04 |
| .shファイル | `entry_points/main.py`の薄いラッパー | 直接Streamlit起動 | 2025-08-04 |
| ダッシュボード起動 | `main.py dashboard`のみ | `dashboard.py`重複 | 2025-08-04 |
| スケジューラー | 廃止済み（カタログベース） | nasdaq/aapl_scheduler.py | 2025-08-04 |
| tc→日時変換 | DB保存時に実行済み | ダッシュボードで再計算 | 2025-08-04 |
| データソース | market_data_catalog.json | ハードコード | 2025-08-04 |

#### 3. **変更時の必須プロトコル**
1. **事前確認**: 上記の表を確認
2. **論文再現テスト**: 変更前後で実行
3. **差分確認**: `git diff`で意図しない変更がないか確認
4. **即時記録**: 重要な変更はこのファイルに記録

### 🔒 保護対象
- `tests/historical_crashes/black_monday_1987_validator.py` （100/100スコア維持必須）
- `src/fitting/` 以下のフィッティングアルゴリズム
- 論文数式の実装（logarithm_periodic_func等）
- 歴史的クラッシュ検証機能

### 📋 変更前必須チェック
1. **変更前**: `python tests/historical_crashes/black_monday_1987_validator.py` を実行
2. **変更後**: 同テストを再実行し、100/100スコア維持を確認
3. **破損時**: 即座にgit revertで変更を巻き戻し

## 🎯 このファイルの目的

このファイルは、Claude Code（AI）がプロジェクトを理解する際に最初に参照すべき中核ファイルを明示するものです。

## 📋 必須参照ファイル（優先順位順）

### 1. 進捗管理システム（最優先）
```
docs/progress_management/
├── README.md              # システム概要・運用ルール
├── CURRENT_PROGRESS.md    # 現在の進捗状況
└── CURRENT_ISSUES.md      # アクティブな課題
```
**重要**: タスク開始時は必ずこれらのファイルで現状を確認すること。

### 2. 数学的基礎
```
docs/mathematical_foundation.md
```
**重要**: 実装時は必ず数式と論文を確認すること。

### 3. 実装戦略
```
docs/implementation_strategy.md
```
**重要**: 新機能追加時は全体戦略との整合性を確認すること。

## 🚫 参照を避けるべきファイル

以下は統合・削除対象のため参照しないこと：
- `docs/implementation/Current_System_Architecture.md`
- `docs/implementation/Data_Sources_Analysis.md`
- `docs/implementation/Code_Cleanup_Analysis.md`
- `docs/Data_Acquisition_Strategy.md`

## 📁 プロジェクト構造（2025-08-04更新）

### 🟢 **現在アクティブな構造**

```
sornette_prediction/
├── CLAUDE.md                     # このファイル（AI指示）
├── README.md                     # プロジェクト概要
├── USER_EXECUTION_GUIDE.md       # ユーザー実行ガイド
│
├── 🔴 scheduled_nasdaq_analysis.py   # 削除済み（カタログベースに移行）
├── 🔴 scheduled_aapl_analysis.py     # 削除済み（カタログベースに移行）  
├── 🟢 start_symbol_dashboard.sh      # ダッシュボード起動
├── 🟡 debug_*.py, test_*.py...       # 一時ファイル群（Issue I017）
│
├── docs/                         # ドキュメント（中核3ディレクトリ）
│   ├── progress_management/      # 🎯 中央管理システム
│   ├── mathematical_foundation.md # 🎯 数学的基礎
│   ├── implementation_strategy.md # 🎯 実装戦略
│   ├── api_guides/               # API統合ガイド
│   ├── analysis/                 # パラメータ分析
│   └── validation_results/       # 検証結果
│
├── src/                          # ソースコード（活発に使用中）
│   ├── 🚫 main.py                   # 存在しない（要実装）
│   ├── 🟢 fitting/                  # LPPLフィッティング（中核）
│   │   ├── fitter.py             # 数学的実装（保護対象）
│   │   ├── multi_criteria_selection.py  # 選択システム
│   │   └── fitting_quality_evaluator.py # 品質評価
│   ├── 🟢 data_sources/             # データ取得（統合システム）
│   │   └── unified_data_client.py # FRED + Alpha Vantage
│   ├── 🟢 database/                 # データベース（SQLite）
│   │   ├── results_database.py    # 結果管理
│   │   └── integration_helpers.py # 統合ヘルパー
│   └── 🟢 web_interface/            # 可視化（Streamlit）
│       └── symbol_visualization_dashboard.py  # メインUI
│
├── 🟢 tests/historical_crashes/     # 論文再現（保護対象）
│   ├── black_monday_1987_validator.py  # 100/100スコア維持必須
│   └── dotcom_bubble_2000_validator.py # 副次検証
├── 🟢 examples/basic_analysis.py    # デモ・テスト統合システム
├── 🟢 results/analysis_results.db   # SQLiteデータベース
└── papers/                       # 参照論文
```

### 🔄 **実際のデータフロー**

```
Entry Points (Root Level)         Core Modules (src/)              Output
┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────┐
│ scheduled_nasdaq_*.py   │────→ │ unified_data_client.py  │────→ │ Raw Market Data │
│ scheduled_aapl_*.py     │      └─────────────────────────┘      └─────────────────┘
│ examples/basic_*.py     │                   │                             │
└─────────────────────────┘                   ▼                             ▼
                                   ┌─────────────────────────┐      ┌─────────────────┐
                                   │ fitting/fitter.py       │────→ │ LPPL Parameters │
                                   │ multi_criteria_*.py     │      │ Quality Metrics │
                                   └─────────────────────────┘      └─────────────────┘
                                               │                             │
                                               ▼                             ▼
                                   ┌─────────────────────────┐      ┌─────────────────┐
                                   │ results_database.py     │────→ │ SQLite Storage  │
                                   │ integration_helpers.py  │      │ Historical Data │
                                   └─────────────────────────┘      └─────────────────┘
                                               │                             │
                                               ▼                             ▼
┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────┐
│ ./start_dashboard.sh    │────→ │ symbol_visualization    │────→ │ Web Dashboard   │
│ (User Interface)        │      │ _dashboard.py          │      │ localhost:8501  │
└─────────────────────────┘      └─────────────────────────┘      └─────────────────┘
```

## 🔄 更新ルール

1. **新規ドキュメント作成前**: 既存の中核ファイルで対応可能か確認
2. **タスク開始時**: 必ず進捗管理システムを参照
3. **実装時**: 数学的基礎との整合性を確認
4. **完了時**: 進捗管理システムを更新

## ⚠️ 重要な注意事項

1. **ドキュメント重複を避ける**: 新規作成前に既存ファイルを必ず確認
2. **中核ファイル優先**: 情報が散在している場合は中核ファイルを信頼
3. **定期的な統合**: 関連情報は中核ファイルに集約

## 🎯 クイックスタート

Claude Code としてこのプロジェクトで作業を開始する場合：

1. このファイル（CLAUDE.md）を読む
2. `docs/progress_management/CURRENT_PROGRESS.md` で現状確認
3. `docs/progress_management/CURRENT_ISSUES.md` で課題確認
4. 必要に応じて `docs/mathematical_foundation.md` を参照

## 🤖 **Claude Code向け継続的プロジェクト理解システム**

### 【重要】毎回の作業開始時の必須手順

Claude Codeが作業を開始する際は、**必ず以下の順序**で情報を確認すること：

#### 1. 中核情報の優先読み込み
```
必須読み込み順序：
1. CLAUDE.md (このファイル) - プロジェクト全体理解
2. docs/progress_management/CURRENT_PROGRESS.md - 現在の進捗
3. docs/progress_management/CURRENT_ISSUES.md - アクティブな課題
4. システム構造の最新状況確認 - アクティブなコード特定
```

#### 2. アクティブなコード構造理解（2025-08-04現在）

**🟢 主要エントリポイント（現在稼働中）**：
- `applications/analysis_tools/crash_alert_system.py` - カタログベース包括解析
- `applications/analysis_tools/market_analyzer.py` - 市場リスク分析
- `applications/examples/basic_analysis.py` - デモ・テスト用統合システム
- `applications/dashboards/main_dashboard.py` - Streamlitダッシュボード

**🟢 中核モジュール（src/以下、活発に使用中）**：
- `src/fitting/` - LPPLフィッティング（科学的中核、100/100スコア保護対象）
  - `fitter.py` - 数学的実装（絶対保護）
  - `multi_criteria_selection.py` - 選択システム
  - `fitting_quality_evaluator.py` - 品質評価
- `src/data_sources/unified_data_client.py` - 統合データクライアント（FRED + Alpha Vantage）
- `src/database/` - SQLite結果管理システム
- `src/web_interface/` - Streamlit可視化システム

**🟡 一時的ファイル（整理対象、Issue I017）**：
- Root直下の `debug_*.py`, `test_*.py`, `create_*.py` など（散在問題）

#### 3. データフロー理解

```
実際の動作フロー：
Entry Points → Data Manager → LPPL Fitting → Database → Dashboard
     ↓             ↓           ↓           ↓         ↓
crash_alert    market_data  fitter.py    SQLite   main_dashboard
 _system.py    _manager.py  (core/fit)   (infra)  (applications)
```

#### 4. システムヘルス確認

**作業前に以下を必ず確認**：
- **論文再現保護**：`python tests/historical_crashes/black_monday_1987_validator.py` が100/100スコア
- **データベース存在**：`results/analysis_results.db` の状態と接続性
- **環境設定**：API認証情報（FRED_API_KEY, ALPHA_VANTAGE_API_KEY）の有効性

### 【新規】プロジェクト構造把握支援機能

#### A. 自動構造解析機能
**新しい作業開始時は Agent tool を使用して**：
1. **最新のファイル構造変更を把握** - git status, 新規ファイル確認
2. **新しいスクリプトや廃止されたファイルを特定** - アクティブ/非アクティブ判定
3. **アクティブなデータフローを確認** - import関係とエントリポイント特定

#### B. 継続的品質保証
- **毎回の変更後**：論文再現テスト実行（100/100スコア維持確認）
- **重要な変更時**：Issue管理ファイル更新（CURRENT_ISSUES.md）
- **構造変更時**：このCLAUDE.mdファイル更新（最新構造反映）

#### C. コンテキスト維持戦略
1. **変更時即時更新**：重要な変更は即座にCLAUDE.mdに反映
2. **Issue連携**：新しい問題は必ずCURRENT_ISSUES.mdに記録・追跡
3. **進捗追跡**：完了した作業はCURRENT_PROGRESS.mdに記録・更新

#### D. 緊急時対応プロトコル
- **論文再現破損時**：即座にgit revert実行
- **データベース破損時**：backup/restore手順実行
- **API認証失敗時**：環境変数と認証情報確認

## 🏗️ **将来の理想的プロジェクト構造（移行目標）**

### 【重要】Issue I017解決のための構造再設計

現在のRoot散在問題を解決するため、以下の理想的構造への移行を計画：

```
sornette_prediction/
├── 🧠 core/                           # 【保護対象】科学的中核理論
│   ├── sornette_theory/               # 純粋なSornette LPPL実装
│   ├── fitting/                       # フィッティングアルゴリズム
│   └── validation/                    # 歴史的検証（100/100スコア保護）
│
├── 🔧 applications/                   # アプリケーション層
│   ├── schedulers/                    # 解析スケジューリング
│   │   ├── nasdaq_scheduler.py        # (scheduled_nasdaq_analysis.py移行)
│   │   └── aapl_scheduler.py          # (scheduled_aapl_analysis.py移行)
│   ├── dashboards/                    # Webインターフェース層
│   │   ├── main_dashboard.py          # 中央ダッシュボード
│   │   └── symbol_dashboard.py        # 銘柄別ビュー
│   ├── analysis_tools/                # 解析アプリケーション
│   │   ├── market_analyzer.py         # (comprehensive_market_analysis.py移行)
│   │   └── retrospective_analyzer.py  # (retrospective_nasdaq_analysis.py移行)
│   └── examples/                      # 実行例
│       ├── quick_start.py             # 基本デモ
│       └── crash_reproduction.py      # 1987年再現デモ
│
├── 🔍 infrastructure/                 # インフラ・サポート
│   ├── data_sources/                  # (現在のsrc/から移行)
│   ├── database/                      # (現在のsrc/から移行)
│   ├── visualization/                 # (現在のsrc/から移行)
│   └── monitoring/                    # 監視システム
│
├── 🧪 dev_workspace/                  # Claude開発ワークスペース
│   ├── debugging/                     # デバッグユーティリティ
│   │   ├── environment_check.py       # (check_environment.py移行)
│   │   └── lppl_viz_debug.py          # (debug_*.py移行)
│   ├── experiments/                   # 実験的機能
│   ├── testing/                       # 開発テスト
│   │   └── test_runner.py             # (run_tests.py移行)
│   └── utilities/                     # 開発ユーティリティ
│
└── 🎯 entry_points/                   # 中央コマンドインターフェース
    ├── main.py                        # メインエントリポイント
    ├── dashboard.py                   # ダッシュボード起動
    ├── scheduler.py                   # スケジューラ起動
    └── validator.py                   # 検証実行
```

### 🚨 **移行時の科学的保護プロトコル**

**移行前後で必須実行**：
```bash
# 移行前
python tests/historical_crashes/black_monday_1987_validator.py

# 移行後  
python core/validation/crash_validators/black_monday_1987_validator.py
# 期待結果: 100/100スコア維持必須
```

### 🎯 **移行により実現される利点**

1. **関心の分離明確化**：
   - `core/` - 科学的理論（不変・保護）
   - `applications/` - ユーザー機能（変更可能）
   - `infrastructure/` - サポートシステム（交換可能）
   - `dev_workspace/` - 開発ユーティリティ（使い捨て）

2. **Claude開発効率向上**：
   - 専用のワークスペース領域
   - デバッグツールの明確な配置
   - 実験機能の分離

3. **拡張性確保**：
   - 新しいスケジューラ・ダッシュボード追加が容易
   - 新市場・銘柄対応の明確な拡張ポイント
   - モジュラー設計による独立開発支援

### 📋 **移行戦略**

**Phase 1** (Week 1): 科学的中核保護 - **CRITICAL**
**Phase 2** (Week 2): アプリケーション層 - **HIGH**  
**Phase 3** (Week 3): インフラ移行 - **MEDIUM**
**Phase 4** (Week 4): 開発ワークスペース - **LOW**

### 🤖 **Claude作業支援**

この構造により、Claude Code は：
- 明確な作業領域 (`dev_workspace/`) を持つ
- 保護すべき中核 (`core/`) を明確に識別
- 安全に実験可能な領域 (`experiments/`) を利用
- 統一されたエントリポイント (`entry_points/`) で操作

---

**最終更新**: 2025-08-04 (理想的構造設計追加)
**管理者**: プロジェクトオーナー + Claude Code
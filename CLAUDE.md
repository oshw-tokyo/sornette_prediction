# Claude Code Instructions - 中核ファイル優先参照指示

## 🚨 **最重要原則: 論文再現の絶対保護**

**⚠️ CRITICAL: この原則は他のすべての要求・変更に優先します**

```
論文再現機能（特にSornette論文のLPPLモデル実装）は
システムの科学的根幹であり、いかなる変更・改修においても
絶対に破損させてはいけません。
```

### 🔒 保護対象
- `core/validation/crash_validators/black_monday_1987_validator.py` （100/100スコア維持必須）
- `core/fitting/` 以下のフィッティングアルゴリズム
- 論文数式の実装（logarithm_periodic_func等）
- 歴史的クラッシュ検証機能

### 📋 変更前必須チェック
```bash
# 変更前・後で必ず実行（統一エントリーポイント経由）
python entry_points/main.py validate --crash 1987
# 期待結果: 100/100スコア維持必須
```

**科学的検証が破損した場合は即座にgit revertで変更を巻き戻してください。**

---

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

---

## 📁 プロジェクト構造（現在の実装）

### 🏗️ **4層アーキテクチャ（確立済み）**

```
sornette_prediction/
├── CLAUDE.md                          # このファイル（AI指示書）
├── README.md                          # プロジェクト概要
├── USER_EXECUTION_GUIDE.md            # ユーザー実行ガイド
│
├── entry_points/                      # 【第1層】統一エントリーポイント
│   ├── main.py                        # 中央コマンドインターフェース（唯一の実行点）
│   └── validator.py                   # 検証専用エントリー
│
├── core/                              # 【第2層】科学的中核（絶対保護対象）
│   ├── fitting/                       # LPPLフィッティング（科学的根幹）
│   │   ├── fitter.py                  # 数学的実装（論文再現・保護対象）
│   │   ├── multi_criteria_selection.py # 選択システム
│   │   └── fitting_quality_evaluator.py # 品質評価
│   ├── sornette_theory/               # 理論実装
│   │   ├── lppl_model.py              # LPPL数学モデル
│   │   └── theory_validation.py       # 理論検証
│   └── validation/                    # 歴史的検証（100/100スコア保護）
│       ├── crash_validators/          # クラッシュ検証
│       └── reproducibility/          # 再現性検証
│
├── applications/                      # 【第3層】アプリケーション層
│   ├── analysis_tools/                # 分析ツール
│   │   ├── crash_alert_system.py      # カタログベース包括解析
│   │   ├── market_analyzer.py         # 市場リスク分析
│   │   └── stock_analyzer.py          # 個別株分析
│   ├── dashboards/                    # Webインターフェース
│   │   ├── main_dashboard.py          # メインダッシュボード
│   │   └── symbol_dashboard.py        # 銘柄別ダッシュボード
│   └── examples/                      # 実行例・デモ
│       ├── basic_analysis.py          # 基本分析デモ
│       └── simple_symbol_analysis.py  # 個別銘柄分析
│
├── infrastructure/                    # 【第4層】インフラ・サポート層
│   ├── data_sources/                  # データ取得
│   │   ├── unified_data_client.py     # FRED + Alpha Vantage統合
│   │   ├── market_data_catalog.json   # 25銘柄・7カテゴリカタログ
│   │   ├── market_data_manager.py     # カタログベース管理
│   │   └── api_rate_limiter.py        # API制限管理
│   ├── database/                      # データベース（SQLite）
│   │   ├── results_database.py        # 結果管理
│   │   └── integration_helpers.py     # 統合ヘルパー（tc→日時変換実装済み）
│   └── visualization/                 # 可視化ツール
│       ├── lppl_visualizer.py         # LPPL専用可視化
│       └── crash_prediction_visualizer.py # 予測可視化
│
├── tests/                             # テストコード
│   └── historical_crashes/            # 論文再現（保護対象）
│       ├── black_monday_1987_validator.py # 100/100スコア維持必須
│       └── dotcom_bubble_2000_validator.py # 副次検証
│
├── results/                           # 分析結果
│   └── analysis_results.db            # SQLiteデータベース
│
├── docs/                              # ドキュメント
│   ├── progress_management/           # 進捗・Issue管理システム
│   ├── mathematical_foundation.md     # 数学的基礎（論文再現結果含む）
│   └── implementation_strategy.md     # 実装戦略
│
└── papers/                            # 論文アーカイブ
    └── extracted_texts/               # テキスト変換済み論文（PDFは禁止）
```

### 🔄 **実際のデータフロー**

```
統一エントリーポイント → インフラ層 → 科学的中核 → アプリケーション層
          ↓                ↓        ↓         ↓
   entry_points/main.py → infrastructure → core → applications
   ├─ analyze ALL       → data_sources  → fitting → analysis_tools  
   ├─ analyze SYMBOL    → database      → validation → dashboards
   ├─ dashboard         → visualization → -------- → examples
   └─ validate --crash  → ------------- → -------- → ---------
                                ↓
                     SQLite Storage + Web Dashboard
                     (results/analysis_results.db + localhost:8501)
```

---

## 🎯 システム機能概要

### 📊 **カタログベース市場分析システム**
- **25銘柄・7カテゴリ** (us_indices, crypto_assets, sector_indices, REITs等)
- **FRED API優先** + Alpha Vantageフォールバック
- **4段階リスク評価** (CRITICAL/HIGH/MEDIUM/LOW)
- **投資判断支援** (ポジションサイズ推奨付き)
- **API制限管理** (自動待機・進捗表示)

### 🧪 **論文再現システム**
- **1987年ブラックマンデー検証** (100/100スコア保護)
- **2000年ドットコムバブル検証** (定性的検証)
- **tc→datetime変換** (時間精度対応、DB保存時実行済み)

### 🚀 **統一実行インターフェース**
```bash
# 全機能へのアクセスはentry_points/main.pyのみ
python entry_points/main.py analyze ALL      # カタログ全銘柄包括解析
python entry_points/main.py analyze SYMBOL   # 個別銘柄解析
python entry_points/main.py dashboard        # ダッシュボード起動
python entry_points/main.py validate         # 論文再現テスト
```

---

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

#### 2. システムヘルス確認（作業前必須）
```bash
# 論文再現保護（最重要）
python entry_points/main.py validate --crash 1987
# 期待結果: 100/100スコア

# 統合テスト
./run_tests.sh

# データベース状態確認
ls -la results/analysis_results.db
```

#### 3. カタログベース解析システム理解
- **market_data_catalog.json**: 25銘柄・7カテゴリの完全定義
- **crash_alert_system.py**: 包括解析のメインエンジン
- **api_rate_limiter.py**: API制限管理（FRED 120req/min, Alpha Vantage 25req/day）

---

## 🛡️ **実装保護ガイドライン（Claude Code向け）**

### AIによる実装ミス防止のための明確な指針

| 機能 | 正しい実装 | よくある誤り | 備考 |
|------|------------|--------------|------|
| **実行エントリポイント** | `entry_points/main.py`のみ使用 | 個別スクリプト直接実行 | 統一原則 |
| **テスト実行** | `python entry_points/main.py validate --crash 1987` | `python tests/.../validator.py` | 2025-08-04統一 |
| **統合テスト** | `./run_tests.sh` (統一ランナー) | `python -m unittest discover` | 論文再現最優先 |
| **tc→日時変換** | DB保存時に実行済み (`integration_helpers.py`) | ダッシュボードで再計算 | 時間精度対応済み |
| **モジュールimport** | `core.fitting.*`, `infrastructure.*` | `src.fitting.*` (旧構造) | 4層アーキテクチャ |
| **シェルスクリプト** | `entry_points/main.py`を呼び出す薄いラッパー | Streamlit直接起動 | 統一インターフェース |
| **データ取得** | `market_data_catalog.json`ベース | ハードコード銘柄 | カタログベース原則 |

### 🚨 **絶対に変更してはいけない保護対象**

- **`core/fitting/fitter.py`** - 数学的実装（論文再現の根幹）
- **`core/validation/crash_validators/black_monday_1987_validator.py`** - 100/100スコア維持必須
- **`infrastructure/database/integration_helpers.py`** - tc→日時変換ロジック（時間精度対応済み）
- **`entry_points/main.py`** - 統一エントリーポイント
- **`infrastructure/data_sources/market_data_catalog.json`** - 25銘柄カタログ定義

### 🔍 **変更前の必須確認事項**

1. **論文再現テスト**: `python entry_points/main.py validate --crash 1987`
2. **統合テスト**: `./run_tests.sh`
3. **アーキテクチャ整合性**: 4層構造（entry_points, core, applications, infrastructure）の維持
4. **カタログベース原則**: 新銘柄追加はmarket_data_catalog.jsonで管理

---

## 📝 **スケジューリング機能について（参考情報）**

### 廃止済みスケジューラーからの参考設計

**旧システムの有用な設計思想**（カタログベースシステムで参考）：
- **週次スケジュール**: 一週間ごとの解析を基本。初回のデータ作成時に過去N週間。また、１週間の解析に際して、基準となる日を設ける(曜日ベースが混乱がなくてよいか)
- **365日データウィンドウ**: 1年間の価格データで解析
- **FRED優先取得**: 安定性重視のデータソース選択
- **複数期間解析**: 時系列での予測精度向上

**現在のカタログベースシステムでの実現方法**：
```bash
# 定期解析の実現（推奨）
python entry_points/main.py analyze ALL  # 全銘柄包括解析
# または
cron job設定でentry_points/main.py呼び出し
```

**注意**: 個別スケジューラー（nasdaq_scheduler.py, aapl_scheduler.py等）は**完全廃止済み**。カタログベースシステムでの統一管理が正式採用。

---

## 🔄 更新ルール

1. **新規ドキュメント作成前**: 既存の中核ファイルで対応可能か確認
2. **タスク開始時**: 必ず進捗管理システムを参照
3. **実装時**: 数学的基礎との整合性を確認
4. **完了時**: 進捗管理システムを更新
5. **重要な変更時**: このCLAUDE.mdファイルを即座に更新

## ⚠️ 重要な注意事項

1. **ドキュメント重複を避ける**: 新規作成前に既存ファイルを必ず確認
2. **中核ファイル優先**: 情報が散在している場合は中核ファイルを信頼
3. **定期的な統合**: 関連情報は中核ファイルに集約
4. **PDF読み込み禁止**: 必ず`papers/extracted_texts/`のテキスト版を使用

---

## 🎯 クイックスタート

Claude Code としてこのプロジェクトで作業を開始する場合：

1. このファイル（CLAUDE.md）を読む
2. `docs/progress_management/CURRENT_PROGRESS.md` で現状確認
3. `docs/progress_management/CURRENT_ISSUES.md` で課題確認
4. `python entry_points/main.py validate --crash 1987` で論文再現確認
5. 必要に応じて `docs/mathematical_foundation.md` を参照

---

**最終更新**: 2025-08-04 (現在の実装ベース・矛盾解消・カタログベース統一)
**管理者**: プロジェクトオーナー + Claude Code
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

## 🕐 **最重要概念: 分析基準日の定義**

**⚠️ CRITICAL: この概念は全実装で必ず遵守すること**

### **分析基準日 (Analysis Basis Date) の定義**
```
分析基準日 = 分析対象期間の最終日
例: 2024-01-01〜2025-08-01の365日間のデータを分析する場合
    → 分析基準日は2025-08-01
```

### **🚨 重要な区別**
- **分析基準日 (analysis_basis_date)**: データ期間の最終日 ← **表示・ソートの基準**
- **フィッティング基準日**: 分析基準日の別名（ダッシュボード表示での用語）
- **基準日**: 分析基準日・フィッティング基準日の簡略表現
- **分析実行日 (analysis_date)**: 実際に計算を実行した日時 ← 表示・ソート対象外

### **実装時の必須ルール**
1. **ダッシュボード表示**: 必ず `analysis_basis_date` でソート
2. **データ取得クエリ**: `ORDER BY analysis_basis_date DESC`
3. **時系列表示**: 分析基準日をX軸に使用
4. **履歴管理**: 同一銘柄の分析基準日ベースで重複管理

### **❌ 避けるべき実装パターン**
```sql
-- ❌ 間違い: 実行日でソート
ORDER BY analysis_date DESC

-- ✅ 正しい: 基準日でソート  
ORDER BY analysis_basis_date DESC
```

### **背景説明**
- フィッティング結果は「その時点までのデータに基づく予測」
- 重要なのは「いつまでのデータで分析したか」（基準日）
- 「いつ計算したか」（実行日）は技術的メタデータに過ぎない

**この概念違反は科学的解釈の誤りを招くため、論文再現保護と同等に重要です。**

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
├── .env                               # 🔐 API認証設定（自動読み込み対応）
│
├── entry_points/                      # 【第1層】統一エントリーポイント
│   ├── main.py                        # 中央コマンドインターフェース（.env自動読込機能付き）
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
│   │   ├── crash_alert_system.py      # カタログベース包括解析・アラートシステム
│   │   └── scheduled_analyzer.py      # 定期分析システム
│   ├── dashboards/                    # Webインターフェース
│   │   ├── main_dashboard.py          # メインダッシュボード（統合済み）
│   │   └── dashboard_launcher.py      # ダッシュボード起動システム
│   ├── examples/                      # 実行例・デモ
│   │   ├── basic_analysis.py          # 基本分析デモ
│   │   ├── simple_symbol_analysis.py  # 個別銘柄分析
│   │   └── validation_demo.py         # 検証デモ
│   └── schedulers/                    # スケジューラー（アーカイブ構造）
│
├── infrastructure/                    # 【第4層】インフラ・サポート層
│   ├── data_sources/                  # データ取得
│   │   ├── unified_data_client.py     # FRED + Alpha Vantage統合
│   │   ├── market_data_catalog.json   # 16銘柄・多カテゴリカタログ
│   │   ├── market_data_manager.py     # カタログベース管理
│   │   └── api_rate_limiter.py        # API制限管理
│   ├── database/                      # データベース（SQLite）
│   │   ├── results_database.py        # 結果管理
│   │   └── integration_helpers.py     # 統合ヘルパー（tc→日時変換実装済み）
│   └── visualization/                 # 可視化ツール
│       └── lppl_visualizer.py         # LPPL専用可視化（PNG無効化対応）
│
├── tests/                             # テストコード
│   ├── historical_crashes/            # 歴史的クラッシュ検証
│   ├── reproducibility_validation/    # 再現性検証システム（保護対象）
│   ├── market_data/                   # 市場データテスト
│   ├── fitting/                       # フィッティングテスト
│   └── api_tests/                     # API接続テスト
│
├── results/                           # 分析結果（クリーンアップ済み）
│   ├── analysis_results.db            # SQLiteデータベース
│   └── crash_alerts/                  # アラート出力ファイル
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
   ├─ analyze ALL       → data_sources  → fitting → crash_alert_system  
   ├─ analyze SYMBOL    → database      → validation → main_dashboard
   ├─ dashboard         → visualization → -------- → scheduled_analyzer
   ├─ validate --crash  → ------------- → -------- → examples
   └─ scheduled-analysis → ------------- → -------- → ---------
                                ↓
                     SQLite Storage + Web Dashboard + Alert System
                     (results/analysis_results.db + crash_alerts/ + localhost:8501)
```

---

## 🔧 **環境変数・API認証設定**

### 📄 **.envファイル自動読み込み機能**

```bash
# プロジェクトルート/.env ファイル（必須）
FRED_API_KEY=your_fred_api_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
```

**特徴**:
- `entry_points/main.py` 実行時に**自動読み込み**
- 手動 `source .env` 不要
- 起動時にAPIキー設定状況を表示・確認
- python-dotenv を使用した安全な読み込み

**APIキー取得方法**:
- **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html (無料・無制限)
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (無料・500req/日)

---

## 🎯 システム機能概要

### 📊 **カタログベース市場分析システム**
- **16銘柄・多カテゴリ** (us_indices, crypto_assets, sector_indices, REITs等)
- **FRED API優先** + Alpha Vantageフォールバック
- **4段階リスク評価** (CRITICAL/HIGH/MEDIUM/LOW)
- **投資判断支援** (ポジションサイズ推奨付き)
- **API制限管理** (自動待機・進捗表示)
- **統合アラートシステム** (crash_alert_system.py)

### 🕐 **定期スケジュール分析システム** ⭐⭐⭐⭐⭐ **要件定義完了**
- **自動スケジュール実行**: 毎週土曜日朝の定期分析（頻度設定可能）
- **時系列データ蓄積**: 継続的な予測履歴の構築・追跡
- **差分実行**: 重複回避による効率的なデータ更新
- **バックフィル機能**: 初回実行時の過去データ自動蓄積
- **分析基準日**: フィッティング期間最終日基準の科学的予測
- **予測有効期限**: 時間経過による予測精度劣化の自動管理

**📋 詳細仕様**: 
- `docs/scheduled_analysis_requirements.md` - 完全要件定義
- `docs/theoretical_validation.md` - 理論的妥当性検証 (✅ 5/5推奨)

### 🧪 **論文再現システム**
- **1987年ブラックマンデー検証** (100/100スコア保護)
- **2000年ドットコムバブル検証** (定性的検証)
- **tc→datetime変換** (時間精度対応、DB保存時実行済み)

### 📊 **可視化システム**
- **Webダッシュボード**: リアルタイム・インタラクティブ可視化
- **PNG自動保存**: デフォルト無効化（Issue I032解決済み）
- **メモリ効率**: 不要なファイル生成を回避

### 🚀 **統一実行インターフェース**
```bash
# 全機能へのアクセスはentry_points/main.pyのみ
python entry_points/main.py analyze ALL      # カタログ全銘柄包括解析
python entry_points/main.py analyze SYMBOL   # 個別銘柄解析
python entry_points/main.py dashboard        # ダッシュボード起動
python entry_points/main.py validate         # 論文再現テスト

# 🕐 定期解析システム（実装中）
python entry_points/main.py scheduled-analysis run     # 定期解析実行
python entry_points/main.py scheduled-analysis backfill --start 2024-01-01  # 過去データ蓄積
python entry_points/main.py scheduled-analysis status  # 解析状態確認
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

#### 3. **🚨 実装前の必須確認事項（重複・誤変更防止）**

**Claude Codeは実装開始前に必ず以下を確認すること**：

##### A. **既存実装の詳細調査**
```bash
# 1. 類似機能の存在確認
grep -r "実装したい機能キーワード" applications/ infrastructure/ core/

# 2. 既存ファイルの役割確認  
head -20 既存ファイル名.py  # コメント・docstringを読む

# 3. インポート関係の確認
grep -r "from.*実装対象モジュール" .
```

##### B. **修正対象ファイルの正確な特定**
```bash
# 修正すべきファイルを正確に特定してから実装開始
ls -la applications/analysis_tools/  # 既存の分析ツール確認
ls -la infrastructure/data_sources/  # データソース実装状況確認
```

##### C. **プロジェクト方針との整合性確認**
- **統一エントリーポイント**: `entry_points/main.py`経由以外の実行は禁止
- **カタログベース原則**: ハードコード銘柄禁止、`market_data_catalog.json`ベース必須
- **4層アーキテクチャ**: 新機能は適切な層（core/applications/infrastructure/entry_points）に配置
- **重複禁止**: 既存機能の拡張を優先、新規作成は最後の手段

##### D. **変更禁止対象の確認**
- **`core/fitting/fitter.py`** - 数学的実装（論文再現の根幹）
- **`infrastructure/database/integration_helpers.py`** - tc→日時変換ロジック
- **`entry_points/main.py`** - 統一エントリーポイント（拡張のみ可能）
- **`infrastructure/data_sources/market_data_catalog.json`** - 25銘柄カタログ定義

##### E. **実装方針の決定フロー**
1. **既存機能拡張 > 新規作成**: まず既存コードに機能追加を検討
2. **統合 > 分離**: 関連機能は既存ファイルに統合
3. **テスト実行**: 変更後必ず論文再現テスト実行
4. **段階的実装**: 一度に大きな変更をせず、小さな変更を積み重ね

#### 4. **現在のカタログベース解析システム理解**

##### 🎯 **既実装済みシステム（変更前に必ず確認）**

**A. カタログベース分析の現状**:
- **`applications/analysis_tools/crash_alert_system.py`**: 
  - ✅ **既に分析実行機能を統合済み** (2025-08-05追加)
  - ✅ `run_catalog_analysis()`: カタログベース包括分析
  - ✅ `_analyze_single_symbol()`: 単一銘柄分析＋DB保存
  - ✅ データベース保存・可視化生成まで一貫実装
  - **重要**: これ以上の重複実装は禁止

**B. データソース管理**:
- **`infrastructure/data_sources/market_data_catalog.json`**: 16銘柄（実測値）
  - カテゴリ: us_indices, crypto_assets, sector_indices等
  - **注意**: メタデータは25銘柄と記載されているが実際は16銘柄
- **`infrastructure/data_sources/api_rate_limiter.py`**: API制限管理
- **`infrastructure/data_sources/unified_data_client.py`**: FRED + Alpha Vantage統合

**C. 実行フロー（確定済み）**:
```bash
# 正しいカタログベース分析実行方法
python entry_points/main.py analyze ALL
  ↓
applications/analysis_tools/crash_alert_system.py:main()
  ↓
run_catalog_analysis() で16銘柄を自動分析・DB保存
```

##### 🚫 **実装時の重要な注意事項**

**絶対に避けるべき行為**:
1. **新しい分析エンジンの作成** - `crash_alert_system.py`が既に完備
2. **カタログ読み込み機能の重複実装** - 既存システムが完動
3. **データベース保存機能の再実装** - `AnalysisResultSaver`が統合済み
4. **API制限管理の再発明** - `APIRateLimiter`が実装済み

**正しいアプローチ**:
1. **機能追加**: 既存`crash_alert_system.py`にメソッド追加
2. **パラメータ調整**: 既存メソッドの引数で制御
3. **設定変更**: `market_data_catalog.json`で銘柄・設定管理

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
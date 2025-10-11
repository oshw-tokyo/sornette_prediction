# Claude Code Instructions - 中核ファイル優先参照指示

## 🚀 **新セッション開始時の必須確認事項**

**⚠️ CRITICAL: 新しいセッションを開始する際は、必ず以下の手順に従ってください**

### 📋 **セッション開始チェックリスト**

1. **プロジェクト理解の再構築**
   ```
   必須読み込み順序:
   1. このCLAUDE.mdファイル全体を読み込む
   2. docs/progress_management/CURRENT_PROGRESS.md - 現在の進捗確認
   3. docs/progress_management/CURRENT_ISSUES.md - アクティブな課題確認
   4. git log --oneline -10 で最近のコミット確認
   ```

2. **前回セッションの作業確認**
   - 前回のセッションが途中で終了した可能性を考慮
   - 中途半端な実装がないかチェック
   - ユーザーから前回の作業内容の説明がある場合は、それを優先的に理解

3. **実装状態の確認**
   - フロントエンド: `fco-dashboard-frontend/` の状態
   - バックエンド: `fco-api/` の状態
   - データベース: FCO分析結果の保存状況
   - 依存関係: package.json、requirements.txt の確認

### 🧪 **workspace_for_claude必須使用**

**実験・調査・テストは必ず `workspace_for_claude/` で実行**:
- **プロジェクト直下汚染**: `./test_*.py`, `./debug_*.py` 等の作成を絶対禁止
- **詳細**: [セクション5](#5-claude-ai専用ワークスペース必須遵守)を必読

## 🚨 **最重要原則: 論文再現の絶対保護 & 法的コンプライアンス**

**⚠️ CRITICAL: これらの原則は他のすべての要求・変更に優先します**

### 1. 科学的正確性の維持
```
論文再現機能（特にSornette論文のLPPLモデル実装）は
システムの科学的根幹であり、いかなる変更・改修においても
絶対に破損させてはいけません。
```

### 2. 法的コンプライアンスの厳守 🔒
```
商用サービスとして提供する際は、金融商品取引法の
投資助言業規制を回避するため、以下を厳守：
- 「クラッシュ予測」等の表現を使用しない
- 数値データのみ提供（投資判断を含まない）
- ユーザーが追加分析を行う設計にする
詳細: docs/service_commercialization/legally_compliant_service_specification.md
```

## 🔄 **実運用データフロー検証の必須原則**

**⚠️ CRITICAL: FCO v2.1の実装・デバッグ時は必ず以下のデータフローを検証**

### **End-to-End データフロー検証チェックリスト**

```
生データ取得 → FCO分析 → データベース保存 → API提供 → フロントエンド表示
     ↓            ↓           ↓              ↓           ↓
   必須検証     必須検証    必須検証      必須検証    必須検証
```

### **各段階での検証ポイント**

1. **生データ取得段階**
   - **⚠️ 注意: APIアクセス制限のため、実装中はFREDデータのみで検証**
   - データソース（FRED優先）が正しく動作しているか
   - 取得期間・頻度が適切か（過度なAPI呼び出しを避ける）
   - エラーハンドリングが機能しているか
   - **実装完了後、本番環境でのみ全データソース検証を実施**

2. **FCO分析段階**
   - Boulder LPPLSライブラリのコア計算が変更されていないか
   - DS-LPPLS Confidence計算が正しいか
   - bubble_type判定がFCO公式基準（30%/5%）に準拠しているか
   - predicted_tc → predicted_crash_date変換が正しいか

3. **データベース保存段階**
   - analysis_basis_date（分析基準日）が正しく設定されているか
   - predicted_crash_dateがNULLになっていないか
   - bubble_typeが適切に保存されているか
   - 重複データが防止されているか

4. **API提供段階**
   - エンドポイントが正しいデータを返しているか
   - フィルタリング条件が適切か
   - データ型・形式が仕様通りか

5. **フロントエンド表示段階**
   - データが正しく可視化されているか
   - 不可能な状態（Fitting Date > Crash Date）が表示されていないか
   - NULL/undefined値が適切に処理されているか
   - 全データポイントが表示されているか

### **実装時の必須確認コマンド**

```bash
# データフロー検証スクリプト（workspace_for_claude/に作成して実行）
# ⚠️ 注意: 開発中はFREDデータのみで検証し、APIアクセス数を節約
python workspace_for_claude/verify_data_flow.py --fred-only

# 各段階の個別確認（必要に応じて実行）
python workspace_for_claude/check_database.py         # DB保存確認（ローカルのみ）
python workspace_for_claude/check_api_response.py     # API確認（ローカルのみ）

# 本番環境でのみ実行する完全検証
# python workspace_for_claude/verify_data_flow.py --full  # 全データソース検証
```

### **Issue発生時の対応**

データフローの問題を検出した場合：
1. 即座に`docs/progress_management/CURRENT_ISSUES.md`に記録
2. 影響範囲を特定し、優先度を設定
3. 根本原因を調査（workspace_for_claude/で実験）
4. 修正を実装・テスト
5. データフロー全体の再検証を実施

**この原則は他のすべての実装作業に優先し、常に遵守すること。**

## 🚀 **FCO v2.1 技術スタック移行中（2025年9月14日開始）**

### ⚠️ **重要な方針転換（2025-10-11）**

**Boulder LPPLS準拠FCO → カスタムFCO（過去LPPL準拠）への移行決定**

**経緯**:
1. ✅ Boulder LPPLS統合実装（多重試行+tc未来制約）
2. ✅ 1987年ブラックマンデー検証 → **0% Confidence（失敗）**
3. ✅ 時間単位影響調査 → 時間単位の問題ではない（Boulder LPPLSアルゴリズム自体の問題）
4. 🎯 **カスタムFCO実装**（過去LPPL準拠）へ移行決定

**問題の詳細**:
- Boulder LPPLSフィッティング: 無制約最適化 + ランダム初期値 → パラメータ発散
- 結果: m=2.2 (範囲外: 0.0-1.0), ω=188.7 (範囲外: 2.0-15.0), R²=-1006.52
- 過去LPPL実装: 境界付き最適化 + グリッドサーチ → 同じデータで100/100スコア達成

### 📋 **要件確認ルール（重要）**

**⚠️ 実装前の必須確認事項**：
```
Claude Codeは実装の各段階で、要件が不明瞭な場合は
必ずユーザーに確認を求めること。推測での実装は禁止。

確認すべき項目の例：
- UIデザインの詳細（レイアウト、色、フォント等）
- ビジネスロジックの仕様（計算式、閾値、条件等）
- エラーハンドリングの方針
- パフォーマンス要件
- セキュリティ要件
```

### 🔄 **カスタムFCO移行状況**

**⭐⭐⭐ Phase 2完了 (2025-10-11) ⭐⭐⭐**

**現在の実装ステータス**:
- ✅ Boulder LPPLS多重試行+tc未来制約実装（0% Confidence、問題あり）
- ✅ 時間単位影響調査完了（時間単位の問題ではない）
- ✅ 科学的手法差分抽出完了（FCO vs 過去LPPL）
- ✅ カスタムFCO移行計画策定完了
- ✅ **Phase 1完全成功** (R²=0.9664, 予測誤差5日, omega境界張り付き解消)
- ✅ **Phase 2完全成功** (DS-LPPLS Confidence=41.18%, 予測誤差20日)
- ⏭️ **Phase 3実装予定** → データベース・フロントエンド統合

**Phase 1成功結果 (2025-10-11)**:
- ✅ R² = 0.9664 (目標 > 0.9)
- ✅ tc = 1.2128 (未来予測、境界張り付きなし)
- ✅ omega = 8.5234 (境界張り付き解消、範囲拡大により達成)
- ✅ 予測誤差 = 5日 (目標 ≤ 35日、大幅達成)
- 🎯 1987年ブラックマンデー予測: 実際10/19 vs 予測10/24

**Phase 2成功結果 (2025-10-11)**:
- ✅ DS-LPPLS Confidence = 41.18% (目標 > 30%、大幅達成)
- ✅ 適格フィット数 = 21 / 51 窓
- ✅ 予測誤差 = 20日 (目標 ≤ 60日、大幅達成)
- ✅ R² 範囲 = 0.9423 ~ 0.9739 (平均 0.9643)
- ✅ omega範囲 = 5.3063 ~ 8.6712 (範囲拡大の効果確認)
- 🎯 1987年ブラックマンデー予測: 実際10/19 vs 予測11/08

**重要な改善 (2025-10-11)**:
- ⚠️ **omega範囲拡大**: [5.0, 8.0] → [5.0, 10.0]
  - 根拠: Sornette論文で最大 ω = 8.93 の実例を確認
  - 詳細: papers/extracted_texts/sornette_2004_0301543v1_*.txt
  - 結果: omega境界張り付き問題を解消、予測精度向上（11日→5日）

**実装ファイル**:
- `core/fitting/lppl_optimizer.py` - ⚠️ **CRITICAL** グリッドサーチ + 境界付き最適化（詳細コメント済み）
- `core/fitting/custom_fco_engine.py` - ⚠️ **CRITICAL** 多重窓FCOエンジン（Phase 2実装予定、詳細コメント済み）
- `core/fitting/lppl_utils.py` - 時間正規化・LPPL関数定義
- `workspace_for_claude/test_custom_fco_phase1_with_plot.py` - Phase 1検証スクリプト（色盲対応プロット）
- `infrastructure/database/fco_results_database.py` - FCO専用DB設計済み
- **データベース方針**: 全126窓のデータを保存（変更なし）

**⚠️⚠⚠️ 変更前の必須確認 ⚠️⚠️⚠️**:
```bash
# Phase 1検証テスト（必須）
python workspace_for_claude/test_custom_fco_phase1_with_plot.py
# 期待結果: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし
```

### 📚 **カスタムFCO移行計画・調査結果**

#### 🎯 **文書体系の全体像**

```
docs/fco_upgrade_v2/              ← FCO関連文書の統合ディレクトリ
│
├── foundation/                   ← 共通基盤（カスタムFCO + Boulder FCO共通）
│   └── MIGRATION_PLAN_CUSTOM_FCO.md  ← 📌 カスタムFCO移行計画（最優先参照）
│
├── v2.1_webapp/                  ← Boulder LPPLS FCO（Webアプリケーション層）
│   ├── fco_v2.1_architecture.md       # React + FastAPI アーキテクチャ
│   └── [その他フロントエンド文書]
│
├── data_engine/                  ← Boulder LPPLS FCO（CLIツール層）
│   ├── README.md                      # fco-daily コマンド仕様
│   └── [その他データエンジン文書]
│
└── archives/deprecated_boulder_plans/ ← 非推奨のBoulder FCO計画（参照禁止）

workspace_for_claude/
└── CUSTOM_FCO_REPRODUCIBILITY_TEST_PLAN.md  ← 📌 テスト実装仕様
```

#### 📌 **カスタムFCO移行計画**（最優先参照）

- **`docs/fco_upgrade_v2/foundation/MIGRATION_PLAN_CUSTOM_FCO.md`** - 📌 **移行計画の完全仕様**
  - Phase 1: 過去実装復元・単一窓検証（2-3日）
    - 成功基準: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし
  - Phase 2: 多重窓解析統合（1週間、最初から126窓）
    - 成功基準: Confidence > 30%, positive_bubble, 精度達成率測定
  - Phase 3: DB/フロントエンド統合（2-3日）
  - Phase 4: 最終検証・最適化（3-5日、2000年・2008年段階的実装）

#### 📋 **再現性テスト計画**（2025-10-11更新）

- **`workspace_for_claude/CUSTOM_FCO_REPRODUCIBILITY_TEST_PLAN.md`** - 📌 **テスト実装の完全仕様**
  - A0: 境界張り付きを失敗として扱う（警告ではなく）
  - A1: 予測誤差≤35日、各窓の精度達成率測定
  - A2: DS-LPPLS Confidence > 30%（FCO標準閾値、選定理由明記）
  - A3: 最初から126窓でテスト（段階的検証不要）
  - A4: 他の歴史的クラッシュは段階的実装（1987年→2000年→2008年）

**科学的根拠**:
- `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md` - 科学的手法差分
  - 時間正規化: [0, 1] vs インデックス
  - 最適化: curve_fit (境界付き) vs minimize (無制約)
  - 初期値: グリッドサーチ (1000回) vs ランダム (25回)
- `archive/src_pre_migration_backup/fitting/fitter.py` - 過去の成功実装（100/100スコア）

**調査結果**:
- `workspace_for_claude/CORRECTED_FINDING_actual_results.md` - データ期間影響の実測値
  - commit a9c7f55: 706日データ、17日誤差（クラッシュ3日前基準）
  - グリッドサーチ: 1000日データ、35日誤差（60日前基準、科学的に正しい）
- `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md` - 時間単位調査
  - 結論: 時間単位の問題ではない（Boulder LPPLSアルゴリズム自体の問題）
- `docs/progress_management/FCO_IMPROVEMENT_IMPLEMENTATION_SUMMARY.md` - 実装サマリー
- `docs/progress_management/ALTERNATIVE_SOLUTION_PAST_LPPL_TO_FCO.md` - 代替策提案
- `docs/progress_management/ISSUE_I124_FCO_IMPLEMENTATION_VERIFICATION.md` - Issue管理

**旧FCO計画（Boulder LPPLS準拠、⚠️ 非推奨）**:
- `docs/fco_upgrade_v2/archives/deprecated_boulder_plans/` - アーカイブ済み
  - `comparison_fco_vs_current_implementation.md` - 旧比較文書（非推奨）
  - `fco_implementation_gap_analysis.md` - 旧ギャップ分析（非推奨）
- ⚠️ **これらの文書は参照しないこと**（カスタムFCO移行のため）

### 🎯 **並行するFCOシステム: カスタムFCO vs Boulder LPPLS FCO**

#### ⚠️ **重要: 2つのFCO実装の共存**

現在、以下の2つのFCO実装が並行して存在します：

| 実装 | 状態 | アルゴリズム | 文書 | 用途 |
|------|------|-------------|------|------|
| **カスタムFCO** | 🚧 開発中 | 過去LPPL準拠（グリッドサーチ + 境界付き最適化） | `foundation/MIGRATION_PLAN_CUSTOM_FCO.md` | **科学的再現性の保証** |
| **Boulder LPPLS FCO** | ⚠️ 問題あり | Boulder LPPLSライブラリ（無制約最適化） | `v2.1_webapp/`, `data_engine/` | Webアプリ・CLIツール |

#### 🎯 **統合戦略**

**Phase 3完了後の統合**:
```python
# カスタムFCOエンジンが完成後:
core/fitting/fco_engine.py ← custom_fco_engine.py で置き換え
    ↓
v2.1 Webアプリ・Data Engineが自動的にカスタムFCO実装を使用
    ↓
インターフェース互換性維持（APIエンドポイント・CLI変更なし）
```

#### 📁 **Boulder LPPLS FCO文書（参照のみ）**

**FCO v2.1 (Webアプリケーション層)**:
- `docs/fco_upgrade_v2/v2.1_webapp/fco_v2.1_architecture.md` - React+FastAPI アーキテクチャ
- `docs/fco_upgrade_v2/v2.1_webapp/fco_dashboard_integration_guide.md` - フロントエンド統合ガイド
- **注意**: これらはBoulder LPPLS FCO用の文書（カスタムFCO完成後は実装部分を差し替え）

**Data Engine (CLIツール層)**:
- `docs/fco_upgrade_v2/data_engine/README.md` - fco-daily コマンド仕様
- `docs/fco_upgrade_v2/data_engine/fco_v3_complete_architecture.md` - v3システム完全仕様
- **注意**: これらもBoulder LPPLS FCO用（カスタムFCO完成後は自動的に切り替わる）

#### ⚠️ **実装時の注意**

1. **カスタムFCO Phase 1-3**: `core/fitting/custom_fco_engine.py` で開発
2. **Phase 3完了後**: `custom_fco_engine.py` → `fco_engine.py` へ置き換え
3. **v2.1 Webアプリ・Data Engine**: 自動的にカスタムFCO実装を使用（import文は変更なし）
4. **インターフェース互換性**: `FCOEngine.compute_ds_lppls_confidence()` シグネチャを維持

**商用サービス化文書（継続）**:
- `docs/service_commercialization/` - 商用サービス化文書
  - **`sornette-legal-compliance-guide.md`** - 法的コンプライアンスガイド 🔒
  - **`legally_compliant_service_specification.md`** - 法的準拠版仕様書（実装はこれに従う）✅

### 🔒 保護対象

**⚠️⚠️⚠️ CRITICAL: 以下のファイル・機能は絶対に破壊しないこと ⚠️⚠️⚠️**

- **`core/fitting/lppl_optimizer.py`** ⚠️ **Phase 1完了 (2025-10-11)**
  - グリッドサーチ + 境界付き最適化（科学的再現性の根幹）
  - R²=0.9664, 予測誤差5日達成
  - omega範囲 [5.0, 10.0] (Sornette論文準拠、最大8.93確認済み)
  - **変更前必須テスト**: `python workspace_for_claude/test_custom_fco_phase1_with_plot.py`

- **`core/fitting/custom_fco_engine.py`** ⚠️ **Phase 2実装予定**
  - 多重時間窓FCOエンジン（126窓統合）
  - lppl_optimizer.py との境界条件完全一致必須
  - **依存関係**: lppl_utils.py, lppl_optimizer.py

- **`core/fitting/lppl_utils.py`**
  - 時間正規化 [0, 1]
  - logarithm_periodic_func（LPPL数式実装）
  - **変更禁止**: 数式の数学的定義

- **`workspace_for_claude/test_custom_fco_phase1_with_plot.py`**
  - Phase 1検証スクリプト（色盲対応プロット）
  - 成功基準: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし

- `core/validation/crash_validators/black_monday_1987_validator.py` （100/100スコア維持必須）
- 論文数式の実装（logarithm_periodic_func等）
- 歴史的クラッシュ検証機能
- **Boulder LPPLSライブラリのコア計算**（`lppls`パッケージの数学的処理は一切変更禁止）
  - bubble_type判定はアプリケーション層での適切な拡張（変更可）
  - FCO公式基準の閾値（30%/5%）は維持必須
  - 詳細：`workspace_for_claude/boulder_lppls_diff_analysis.md`
- **v1.5 Dashboard Clustering Analysis** （2025-08-14完成・Issue I058で広範なデバッグ済み）
  - Individual Fitting Results統合表示
  - Quality フィルター（4段階選択機能）
  - Distance パラメータ最適化（デフォルト45日）
  - 散布図右端を今日に固定する実装

### 📋 変更前必須チェック
```bash
# 変更前・後で必ず実行（統一エントリーポイント経由）
python entry_points/main.py validate --crash 1987
# 期待結果: 100/100スコア維持必須

# ⚠️ カスタムFCO Phase 1検証テスト（2025-10-11追加）
python tests/custom_fco/test_phase1_single_window.py
# 期待結果: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし
```

**⚠️ カスタムFCOテスト体系 (2025-10-11)**:
- **Phase 1**: `tests/custom_fco/test_phase1_single_window.py` - 単一窓検証（✅ 完了、R²=0.9664、誤差5日）
- **Phase 2**: `tests/custom_fco/test_phase2_multi_window.py` - 多重窓検証（✅ 完了、Confidence=41.18%、誤差20日）

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

### **🛡️ データ品質保護（2025-08-10完全修正）**
- **重複防止**: `INSERT OR REPLACE` + UNIQUE制約で同一銘柄・基準日の重複防止
- **analysis_basis_date自動設定**: データベース保存時に`data_period_end`で自動設定
- **ダッシュボードロバスト性**: プロット要素に一意キー付与で重複データ耐性
- **Issue I048解決**: NULL analysis_basis_date問題を根本修正（647件重複除去）

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

### 4. API割り当て戦略
```
docs/api_assignment_strategy.md
```
**重要**: 新API追加・銘柄変更時は必ず評価基準に従うこと。

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
│   ├── data_sources/                  # データ取得（安定版v1.0）
│   │   ├── unified_data_client.py     # FRED + Twelve Data統合（FRED優先）
│   │   ├── market_data_catalog.json   # 80銘柄カタログ（FRED:24 + Twelve:56）
│   │   ├── fred_data_client.py        # FRED API クライアント（最優先）
│   │   ├── twelvedata_client.py       # Twelve Data クライアント（補完用）
│   │   ├── market_data_manager.py     # カタログベース管理
│   │   └── api_rate_limiter.py        # API制限管理（Twelve Data: 800req/日）
│   ├── database/                      # データベース（重複防止強化）
│   │   ├── results_database.py        # 結果管理（UPSERT + UNIQUE制約）
│   │   └── integration_helpers.py     # 統合ヘルパー（tc→日時変換実装済み）
│   ├── maintenance/                   # メンテナンスツール
│   │   ├── backup_database.sh         # データベース自動バックアップ
│   │   ├── remove_duplicates.py       # 重複データ除去
│   │   ├── start_dashboard.sh         # ダッシュボード起動（統一EP経由）
│   │   └── run_tests.sh               # テスト実行（統一EP経由）
│   └── visualization/                 # 可視化ツール
│       └── lppl_visualizer.py         # LPPL専用可視化（ロバスト性強化）
│
├── tests/                             # テストコード
│   ├── historical_crashes/            # 歴史的クラッシュ検証
│   ├── reproducibility_validation/    # 再現性検証システム（保護対象）
│   ├── market_data/                   # 市場データテスト
│   ├── fitting/                       # フィッティングテスト
│   └── api_tests/                     # API接続テスト
│
├── results/                           # 分析結果
│   ├── analysis_results.db            # SQLiteデータベース
│   ├── backups/                       # データベースバックアップ
│   └── crash_alerts/                  # アラート出力ファイル
│
├── logs/                              # ログファイル
│   ├── data_collection_*.log          # データ収集ログ
│   └── nohup.out                      # バックグラウンド実行ログ
│
├── docs/                              # ドキュメント
│   ├── progress_management/           # 進捗・Issue管理システム
│   ├── mathematical_foundation.md     # 数学的基礎（論文再現結果含む）
│   └── implementation_strategy.md     # 実装戦略
│
├── workspace_for_claude/              # Claude AI専用ワークスペース
│   ├── stable_version_strategy_v2.md  # 安定版v1.0実装戦略（FRED優先）
│   ├── api_evaluation_knowledge_base.md # API評価・問題記録
│   └── [その他の実験・調査ファイル]
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
# CoinGecko API Key（オプション：無料版でも利用可能）
COINGECKO_API_KEY=your_coingecko_api_key_here
```

**特徴**:
- `entry_points/main.py` 実行時に**自動読み込み**
- 手動 `source .env` 不要
- 起動時にAPIキー設定状況を表示・確認
- python-dotenv を使用した安全な読み込み

**APIキー取得方法**:
- **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html (無料・無制限)
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (無料・500req/日)
- **CoinGecko**: https://www.coingecko.com/en/api/pricing (無料・20req/分)

---

## 🎯 システム機能概要

### 📊 **カタログベース市場分析システム（安定版v1.0）**
- **80銘柄** (FRED 24 + Twelve Data 56)
- **2層API戦略**: FRED最優先 → Twelve Data補完
- **FRED優先原則**: 重複銘柄は必ずFRED使用
- **4段階リスク評価** (CRITICAL/HIGH/MEDIUM/LOW)
- **投資判断支援** (ポジションサイズ推奨付き)
- **API制限管理** (レート制限・自動待機・進捗表示)
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

### 📊 **可視化システム (v1.5 Complete Dashboard with Clustering Analysis)**
- **Webダッシュボード v1.5**: 完全統合されたClustering Analysis実装
- **Clustering Analysis Tab**: 時間的クラスタリングによる高精度予測（DBSCAN実装・Quality フィルター付き）
- **Individual Fitting Results**: クラスター内の詳細分析結果表示（Issue I058完全実装）
- **Quality フィルター**: 4段階選択（全て表示/Unstable除外/Acceptable以上/High Qualityのみ）
- **Distance パラメータ**: 最適化されたデフォルト値45日（クラスタリング精度向上）
- **統一期間選択**: サイドバーからの全タブ共通期間コントロール
- **PNG自動保存**: デフォルト無効化（Issue I032解決済み）
- **メモリ効率**: 不要なファイル生成回避、セッション状態最適化

### 🎯 **Crash Prediction Clustering Analytics (I052実装完了・2025-08-13)**
- **R²重み付きクラスタリング**: DBSCAN 1D密度クラスタリング + R²品質重み付け平均
- **統合期間選択UI**: From/To日付選択・期間視覚化プログレスバー・自動範囲計算
- **統計的最適化パラメータ**: 距離10-90日・最小クラスタサイズ2-20（初期値8）・R²閾値0-1.0
- **投資判断支援テーブル**: C1/C2表記・本日からの日数・Weight Mean Date・信頼度評価
- **2D散布図可視化**: フィッティング基準日vs予測クラッシュ日・クラスター中心線・参照線
- **包括的ヘルプシステム**: 理論説明・パラメータガイド・投資判断解釈をexpandable形式
- **ユーザー重視エラーハンドリング**: データ不足時の具体的解決策提示（期間拡張・閾値調整）
- **Apply Button制御**: 期間選択・パラメータ設定の統合制御による予測可能な動作

### 🚀 **統一実行インターフェース**
```bash
# 全機能へのアクセスはentry_points/main.pyのみ
python entry_points/main.py analyze ALL      # カタログ全銘柄包括解析
python entry_points/main.py analyze SYMBOL   # 個別銘柄解析
python entry_points/main.py dashboard        # 🆕 Symbol Filters Dashboard v2 起動
python entry_points/main.py validate --crash 1987  # 論文再現保護テスト（100/100スコア維持）

# 🕐 定期解析システム（要件定義完了）
python entry_points/main.py scheduled-analysis run     # 定期解析実行
python entry_points/main.py scheduled-analysis backfill --start 2024-01-01  # 過去データ蓄積
python entry_points/main.py scheduled-analysis status  # 解析状態確認
```

---

---

## 🆕 **最新実装: Symbol Filters Dashboard Architecture v2** (2025-08-11)

### 🎯 **革新的アーキテクチャの実現**

```
Symbol Filters → Symbol Selection → Apply → ALL Data Access → Display Period Filtering
     ↓               ↓            ↓           ↓                    ↓
銘柄リスト絞り込み → 銘柄選択 → 明示的実行 → 全履歴データ → プロット範囲制御
```

### 🎆 **主要機能**
- **完全分離設計**: 銘柄選択・データアクセス・期間制御の独立性
- **Apply Button制御**: 予測可能な明示的更新制御
- **リアルタイム状態**: 選択と同時のCurrently Selected Symbol更新
- **全データ保証**: Symbol選択後に全履歴データアクセス
- **エラー防止**: Symbol未選択時の適切なガイダンス

### 🛡️ **品質保証**
- ✅ **論文再現保護**: 100/100スコア維持確認済み
- ✅ **後方互換性**: 既存機能完全保持
- ✅ **SQL最適化**: datatype mismatch問題根本解決
- ✅ **パフォーマンス**: 起動時間大幅短縮

### 📚 **関連ドキュメント**
- **要件書**: `docs/dashboard_requirements.md` (v1.1対応更新済み)
- **実装仕様**: `docs/dashboard_implementation_specification.md` (v1.1対応更新済み)

---

## 🤖 **Claude Code向け継続的プロジェクト理解システム**

### 【重要】毎回の作業開始時の必須手順

**⚠️ 注意: 新セッション開始時は、このセクションではなく、ファイル冒頭の「🚀 新セッション開始時の必須確認事項」セクションを参照してください。**

Claude Codeが継続作業を行う際は、**必ず以下の順序**で情報を確認すること：

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
# 論文再現保護（最重要）- LPPL版
python entry_points/main.py validate --crash 1987
# 期待結果: 100/100スコア

# 論文再現保護 - FCO版（2025-09-13実装）
python entry_points/main.py validate --crash 1987 --fco
# 期待結果: DS-LPPLS Confidence > 30%, Positive bubble判定

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
- **`infrastructure/data_sources/market_data_catalog.json`** - 81銘柄カタログ定義（BAMLH0A0HYM2追加）

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
- **`infrastructure/data_sources/market_data_catalog.json`**: 78銘柄（実測値）
  - カテゴリ: us_indices, crypto_assets, sector_indices等
  - **注意**: メタデータは81銘柄と記載されているが実際は78銘柄
- **`infrastructure/data_sources/api_rate_limiter.py`**: API制限管理
- **`infrastructure/data_sources/unified_data_client.py`**: FRED + Alpha Vantage統合

**C. 実行フロー（確定済み）**:
```bash
# 正しいカタログベース分析実行方法
python entry_points/main.py analyze ALL
  ↓
applications/analysis_tools/crash_alert_system.py:main()
  ↓
run_catalog_analysis() で78銘柄を自動分析・DB保存
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

#### 5. **🧪 Claude AI専用ワークスペース（必須遵守）**

**⚠️ 最重要原則**: Claude Codeは**すべての試行錯誤・実験・調査作業**を`workspace_for_claude/`で実行すること

##### A. **🚨 絶対禁止事項（プロジェクト汚染防止）**

```bash
# ❌ 絶対にやってはいけないこと
./test_*.py                    # プロジェクト直下にテストファイル作成
./debug_*.py                   # プロジェクト直下にデバッグファイル作成
./temp_*.py                    # プロジェクト直下に一時ファイル作成
./analyze_*.py                 # プロジェクト直下に分析ファイル作成
./experiment_*.py              # プロジェクト直下に実験ファイル作成

# ✅ 正しい場所
workspace_for_claude/test_*.py      # 実験・テスト専用ディレクトリ
workspace_for_claude/debug_*.py     # デバッグ専用ディレクトリ
workspace_for_claude/analyze_*.py   # 分析専用ディレクトリ
```

##### B. **セッション間認識強化（重要）**

**🎯 Claude Codeへの明確な指示**:
1. **新セッション開始時**: 必ず `CLAUDE.md` → `workspace_for_claude/` セクションを読み直す
2. **任意のファイル作成前**: 「これは`workspace_for_claude/`で行うべきか？」を自問
3. **実験・調査・テスト**: 100%の確率で`workspace_for_claude/`を使用
4. **プロジェクト直下汚染**: いかなる理由があっても禁止

##### C. **ワークスペース必須使用シナリオ**

| 作業内容 | ❌ 間違った場所 | ✅ 正しい場所 | 
|---------|----------------|---------------|
| **APIテスト** | `./test_api.py` | `workspace_for_claude/test_api.py` |
| **デバッグコード** | `./debug.py` | `workspace_for_claude/debug_analysis.py` |
| **コード分析** | `./analyze_code.py` | `workspace_for_claude/code_analysis.py` |
| **プロトタイプ** | `./prototype.py` | `workspace_for_claude/prototype_design.py` |
| **依存関係調査** | `./check_deps.py` | `workspace_for_claude/dependency_analysis.py` |
| **一時的修正テスト** | `./test_fix.py` | `workspace_for_claude/fix_validation.py` |
| **パフォーマンス測定** | `./benchmark.py` | `workspace_for_claude/performance_test.py` |

##### D. **現在のワークスペース内容（参考）**
```bash
workspace_for_claude/
├── api_alternatives_analysis.md        # API代替候補調査結果
├── catalog_analysis.py                 # カタログ分析（今回使用）
├── design_violation_analysis.md        # 設計違反分析レポート
├── unified_data_client_fixed.py        # 修正版実装プロトタイプ
├── unused_code_analysis.md            # 未使用コード分析レポート
├── coingecko_api_test.py               # CoinGecko API テスト
└── test_yahoo_finance.py              # Yahoo Finance APIテスト
```

##### E. **セッション間での記憶維持強化**

**🧠 Claude Code記憶強化策**:

1. **CLAUDE.md冒頭配置**: この指示を最重要セクションで明記
2. **作業前チェックリスト**:
   ```
   □ 新しいファイル作成が必要か？
   □ それは実験・テスト・調査目的か？
   □ YES → workspace_for_claude/ 必須使用
   □ NO → 適切なプロジェクト層に配置
   ```

3. **自動確認プロンプト**:
   ```
   実装前に必ず自問:
   「このファイルは本当にプロジェクト本体に必要か？
    試行錯誤・実験ならworkspace_for_claude/を使うべきでは？」
   ```

##### F. **ワークスペース運用の改善点（2025-08-09）**

**✅ 今回改善したこと**:
- プロジェクト直下の一時ファイル（`test_*.py`, `analyze_catalog.py`等）を完全削除
- 全ての実験・分析作業をworkspace_for_claude/に集約済み
- セッション間での認識継続の仕組み強化

**📋 継続的改善**:
- Claude Codeが新セッション開始時にこのセクションを必ず参照
- プロジェクト汚染の完全防止
- 実験成果の体系的な本体統合

**実装時の指針（更新版）**:
```bash
# ❌ プロジェクト汚染（絶対禁止）
./experimental_api_test.py             # 直下に実験ファイル
applications/analysis_tools/temp_test.py  # 本体に一時ファイル

# ✅ 正しいワークフロー  
workspace_for_claude/experimental_api_test.py  # ワークスペースで実験
↓ (検証成功・実用性確認後)
infrastructure/data_sources/new_api_client.py  # 本体に正式統合
```

---

## 📊 **ダッシュボード詳細仕様（2025-08-12更新）**

### 🎯 **4タブ構成システム**
```
Symbol Analysis Dashboard (Symbol Filters Architecture v2)
├── 🎯 Crash Prediction Clustering     # NEW: Issue I052実装完了
├── 📈 Price Predictions               # Core: LPPL予測表示
├── 🔀 Prediction Convergence          # Advanced: 予測収束解析
└── 📋 Parameter Details               # Technical: パラメータテーブル
```

### 🎯 **Crash Prediction Clustering タブ（Issue I052完了・I054改善実装）**
- **機能概要**: 複数の予測クラッシュ日を時系列クラスタリング分析
- **核心技術**: 1D DBSCAN + R²-weighted average method（I054改善実装）
- **データ品質管理**: 高品質(R² ≥ threshold)・低品質データの自動分離表示
- **Interactive Parameters**:
  - Clustering Distance (10-90 days): DBSCAN eps parameter  
  - Min Cluster Size (2-10): DBSCAN min_samples parameter
  - Future Projection (30-365 days): 将来予測期間表示
  - Min R² for Clustering (0.0-1.0): データ品質フィルタリング閾値
- **Visualization Components（I054改善版）**:
  - **Upper Panel**: 2D scatter plot (Fitting Date vs Predicted Crash Date)
    - Color-coded clusters with **thin horizontal center lines** (width=1)
    - **R²-weighted average method**: No regression assumptions
    - Reference line (Fitting Date = Crash Date) for immediate risk indication
    - High-quality data clustering vs low-quality data separation
  - **Lower Panel**: Cluster statistics bar chart (Average R² scores by cluster)
  - **Statistics Table**: Comprehensive cluster details with weighted/simple STD, IQR
- **Statistical Analysis（I054改善版）**:
  - **R²-weighted average**: Center line from weighted mean of predictions
  - **Uncertainty measures**: Weighted STD, Simple STD, IQR表示
  - **Confidence scoring**: High/Medium/Low based on Avg R² and cluster size
  - **No time-series assumptions**: More statistically robust methodology
  - **Clean visualization**: Removes complex regression lines and uncertainty bands
- **Session State Management**: All parameters persist across interactions
- **Independent Display Period**: タブ独立の期間フィルタリング制御

### 📈 **Price Predictions タブ（既存システム）**
- LPPL曲線フィッティング結果の可視化
- 予測クラッシュ日・価格の表示
- 品質指標（R², confidence interval）の表示

### 🔀 **Prediction Convergence タブ（既存システム）**  
- 複数分析の収束パターン解析
- 時系列での予測安定性評価

### 📋 **Parameter Details タブ（既存システム）**
- 全パラメータの詳細テーブル表示
- CSV ダウンロード機能

### 🚨 **技術的解決済み問題**
- **Getting Started Loop**: st.rerun()無限ループ問題を根本解決
- **Session State Management**: パラメータリセット問題を完全修正
- **Apply Period Independence**: タブ間独立動作の実現
- **Coordinate System**: 回帰線とスキャッタープロット座標系統一
- **Import Dependencies**: sklearn, plotly, scipy等の適切な依存関係管理

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
- **Clustering Analysis Tab実装** - v1.5で完成度向上・広範なデバッグ済み（無闇な変更禁止）
- **Sidebar Period Selection実装** - 全タブ統一期間選択システム（アップデート時は全タブ影響を考慮）
- **`infrastructure/data_sources/market_data_catalog.json`** - 81銘柄カタログ定義（BAMLH0A0HYM2追加）

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

### FCO Historical分析の頻度設定

**本番要件**: `--frequency daily`（日次営業日ベース）
```bash
python entry_points/main.py fco-analyze historical --start-date 1977-01-02 --symbols SP500 --frequency daily
```

**現在の開発状況**（2025-10-10時点）:
- ⚠️ **一時的に`--frequency weekly`を使用中**（計算時間短縮のため）
- SP500全期間解析を週次で実行中（約8.5時間予定）
- 完了後、`--frequency daily`に切り替えて本番相当のデータを生成予定

**理由**:
- 市場営業日ごとの毎日FCO分析が要件（CURRENT_ISSUES.md I117参照）
- 開発段階では週次で効率的にテスト
- 本番移行時に日次へ切り替え（Issue I120のスキップ機能実装後）

---

## ⚠️ **文書整理状況（2025年9月）**

**重要**: FCOレベルアップグレードに伴い、文書構造を大幅に再編成中。
- workspace_for_claude/からdocs/以下への段階的移行を実施
- 今後も精査・整理が必要
- v2.0実装完了後に最終的な文書体系を確立予定

## 🔄 更新ルール

1. **新規ドキュメント作成前**: 既存の中核ファイルで対応可能か確認
2. **タスク開始時**: 必ず進捗管理システムを参照
3. **実装時**: 数学的基礎との整合性を確認
4. **完了時**: 進捗管理システムを更新
5. **重要な変更時**: このCLAUDE.mdファイルを即座に更新

## 🧹 プロジェクト整理方針

**Claude Codeは作業中に以下を継続的に実施すること**：

1. **不要ファイルの特定と報告**
   - 重複するドキュメント
   - 古い実装やアーカイブ可能なファイル
   - 一時的なテストファイル（workspace_for_claude以外）

2. **冗長性の削減**
   - 同じ情報が複数箇所にある場合は統合を提案
   - 使われていないコードや設定ファイルを特定

3. **整理提案のタイミング**
   - 実装作業中に気づいた場合は都度報告
   - ユーザーに確認を取ってから削除/移動
   - プロジェクト構造の改善案も積極的に提案

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

**最終更新**: 2025-08-10 (API効率化完了・Individual Analysis重複解消・BAMLH0A0HYM2追加・Issue I048完全修正)
**管理者**: プロジェクトオーナー + Claude Code
# ドキュメント整理計画 - FCOカスタム実装移行に伴う整理

**作成日**: 2025-10-11
**担当**: Claude Code
**目的**: 代替策（過去LPPL→カスタムFCO）移行に伴うドキュメント構造の整理

---

## 📋 整理方針

### 基本原則

1. **Boulder LPPLS準拠のFCO計画 → アーカイブ**
   - バックエンド実装に関する旧計画は全てアーカイブ
   - 理由: カスタムFCO（過去LPPL準拠）に移行するため

2. **フロントエンド関連 → 保持**
   - React + FastAPI フロントエンド計画は有効
   - 理由: バックエンドAPI変更なし（インターフェース互換）

3. **最新の移行計画 → 中心文書として配置**
   - `MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md` を中心文書化
   - 全ての参照をこの文書に集約

4. **混乱を招く文書 → 削除または明確な非推奨マーク**
   - 実装に混乱をもたらす古い計画は削除
   - 保持する場合は非推奨マークを追加

---

## 🗂️ アーカイブ対象（Boulder LPPLS準拠のバックエンド計画）

### docs/fco_upgrade_v2/foundation/

| ファイル名 | 理由 | 移動先 |
|-----------|------|--------|
| `comparison_fco_vs_current_implementation.md` | Boulder LPPLS準拠の比較文書 | `docs/fco_upgrade_v2/archives/deprecated_boulder_plans/` |
| `fco_implementation_gap_analysis.md` | Boulder LPPLS準拠のギャップ分析 | `docs/fco_upgrade_v2/archives/deprecated_boulder_plans/` |

**実行コマンド**:
```bash
mkdir -p docs/fco_upgrade_v2/archives/deprecated_boulder_plans/
mv docs/fco_upgrade_v2/foundation/comparison_fco_vs_current_implementation.md docs/fco_upgrade_v2/archives/deprecated_boulder_plans/
mv docs/fco_upgrade_v2/foundation/fco_implementation_gap_analysis.md docs/fco_upgrade_v2/archives/deprecated_boulder_plans/
```

### docs/fco_upgrade_v2/ その他

既にアーカイブ済み:
- `docs/fco_upgrade_v2/archives/database_migration/fco_database_migration_strategy.md`
- `docs/fco_upgrade_v2/archives/database_migration/fco_migration_plan.md`
- `docs/fco_upgrade_v2/archives/fco_implementation_summary_report.md`

→ **追加対応不要**（既にアーカイブ済み）

---

## ✅ 保持対象（有効な文書）

### フロントエンド関連（v2.1 Web App）

| ファイル名 | 理由 | アクション |
|-----------|------|----------|
| `docs/fco_upgrade_v2/v2.1_webapp/fco_v2.1_architecture.md` | React+FastAPI アーキテクチャ | **保持** |
| `docs/fco_upgrade_v2/v2.1_webapp/fco_dashboard_integration_guide.md` | フロントエンド統合ガイド | **保持** |

### データエンジン関連

| ファイル名 | 理由 | アクション |
|-----------|------|----------|
| `docs/fco_upgrade_v2/data_engine/fco_full_history_architecture.md` | 履歴データ管理（汎用） | **保持** |
| `docs/fco_upgrade_v2/data_engine/fco_v3_complete_architecture.md` | 完全アーキテクチャ（汎用） | **保持** |
| `docs/fco_upgrade_v2/data_engine/architecture_migration_local_data_storage.md` | ローカルストレージ設計 | **保持** |

### 最新の移行計画（カスタムFCO）

| ファイル名 | 理由 | アクション |
|-----------|------|----------|
| `docs/progress_management/MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md` | **中心文書** | **最優先参照** |
| `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md` | 科学的差分 | **保持** |
| `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md` | 時間単位調査 | **保持** |
| `docs/progress_management/FCO_IMPROVEMENT_IMPLEMENTATION_SUMMARY.md` | 実装サマリー | **保持** |
| `docs/progress_management/ALTERNATIVE_SOLUTION_PAST_LPPL_TO_FCO.md` | 代替策提案 | **保持** |
| `docs/progress_management/ISSUE_I124_FCO_IMPLEMENTATION_VERIFICATION.md` | Issue管理 | **保持** |

---

## 🗑️ 削除対象（混乱を招く古い文書）

**該当なし**

理由:
- 既に archives/ に移動済みの文書は削除不要
- 保持すべき理由がない文書は現時点で特定されていない

---

## 📝 CLAUDE.md 更新内容

### 現在の記述（問題あり）

```markdown
## 🚀 **FCO v2.1 技術スタック移行中（2025年9月14日開始）**

**実装ステータス**：
- `core/fitting/fco_engine.py` - FCOエンジン実装済み
- ...

**詳細仕様書**：
- `docs/fco_upgrade_v2/` - FCOレベルアップグレード文書群
  - `ds_lppls_indicators_detailed_specification.md` - DS-LPPLS指標詳細
  - `technical_implementation_plan.md` - 技術実装計画
  - **`comparison_fco_vs_current_implementation.md`** - FCO方式と現在の実装の詳細比較 🆕
  - ...
```

### 更新後の記述

```markdown
## 🚀 **FCO v2.1 技術スタック移行中（2025年9月14日開始）**

### ⚠️ **重要な方針転換（2025-10-11）**

**Boulder LPPLS準拠FCO → カスタムFCO（過去LPPL準拠）**

**理由**:
- Boulder LPPLSフィッティング: 1987年で0% Confidence（収束失敗）
- 過去LPPL実装: 同じデータで100/100スコア達成
- 時間単位調査: 問題は時間単位ではなくアルゴリズム自体

**現在の実装ステータス**:
- ✅ Boulder LPPLS多重試行+tc未来制約実装（0% Confidence）
- ✅ 時間単位影響調査完了（時間単位の問題ではない）
- ✅ 科学的手法差分抽出完了
- ⏭️ カスタムFCO実装（過去LPPL準拠）へ移行予定

**実装ファイル**:
- `core/fitting/fco_engine.py` - 現在の実装（Boulder LPPLS準拠、問題あり）
- `core/fitting/custom_fco_engine.py` - 新規実装予定（過去LPPL準拠）

**詳細仕様書・移行計画**:
- **`docs/progress_management/MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md`** - 📌 **中心文書**
- `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md` - 科学的手法差分
- `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md` - 時間単位調査結果
- `docs/progress_management/ALTERNATIVE_SOLUTION_PAST_LPPL_TO_FCO.md` - 代替策提案

**旧FCO計画（Boulder LPPLS準拠、非推奨）**:
- `docs/fco_upgrade_v2/archives/deprecated_boulder_plans/` - アーカイブ済み
- ⚠️ これらの文書は参照しないこと（カスタムFCO移行のため）

**フロントエンド計画（有効）**:
- `docs/fco_upgrade_v2/v2.1_webapp/` - React+FastAPI実装計画（継続）
- バックエンドAPI変更なし（インターフェース互換性維持）
```

---

## 📊 参照整合性チェックリスト

### CLAUDE.md

- ✅ FCO移行計画の参照を更新
- ✅ Boulder LPPLS準拠文書を非推奨マーク
- ✅ カスタムFCO移行計画を中心文書化

### README.md

現在の記述を確認:
```bash
grep -n "fco" README.md -i
```

必要に応じて更新（FCO v2.1への言及があれば）

### CURRENT_PROGRESS.md

現在の進捗状況を更新:
- Issue I124の状態: 時間単位調査完了 → カスタムFCO移行フェーズ

### CURRENT_ISSUES.md

Issue I124の更新:
- 状態: 調査完了 → 移行計画策定完了 → ユーザー承認待ち

---

## 🔍 実行手順

### Step 1: アーカイブディレクトリ作成 + ファイル移動

```bash
# アーカイブディレクトリ作成
mkdir -p docs/fco_upgrade_v2/archives/deprecated_boulder_plans/

# Boulder LPPLS準拠の旧バックエンド計画をアーカイブ
mv docs/fco_upgrade_v2/foundation/comparison_fco_vs_current_implementation.md \
   docs/fco_upgrade_v2/archives/deprecated_boulder_plans/

mv docs/fco_upgrade_v2/foundation/fco_implementation_gap_analysis.md \
   docs/fco_upgrade_v2/archives/deprecated_boulder_plans/

# アーカイブ通知ファイル作成
cat > docs/fco_upgrade_v2/archives/deprecated_boulder_plans/README.md <<'EOF'
# アーカイブ: Boulder LPPLS準拠FCO計画（非推奨）

**アーカイブ日**: 2025-10-11
**理由**: カスタムFCO（過去LPPL準拠）への移行に伴い非推奨

これらの文書はBoulder LPPLS（外部ライブラリ）準拠のFCO実装計画です。
2025-10-11の時間単位調査により、Boulder LPPLSでは1987年ブラックマンデーで0% Confidenceとなり、
フィッティング収束しないことが判明しました。

**新しい移行計画**:
- `docs/progress_management/MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md`

⚠️ これらの文書は参照しないでください。
EOF
```

### Step 2: CLAUDE.md 更新

```bash
# CLAUDE.mdのFCOセクションを新しい内容で更新
# （上記の「更新後の記述」を適用）
```

### Step 3: CURRENT_PROGRESS.md / CURRENT_ISSUES.md 更新

```bash
# Issue I124の状態更新
# - 時間単位調査完了
# - カスタムFCO移行計画策定完了
# - ユーザー承認待ち
```

### Step 4: Gitコミット

```bash
git add docs/
git commit -m "📚 ドキュメント整理: カスタムFCO移行に伴うBoulder LPPLS計画アーカイブ"
```

---

## ✅ 完了基準

- ✅ Boulder LPPLS準拠のバックエンド計画をアーカイブ
- ✅ CLAUDE.mdでカスタムFCO移行計画を中心文書化
- ✅ 全ての参照がカスタムFCO移行計画を指す
- ✅ 混乱を招く文書を削除またはアーカイブ
- ✅ フロントエンド計画は保持（有効）

---

## 📝 次のアクション

1. **ユーザー確認**: このドキュメント整理計画の承認
2. **実行**: Step 1-4を実施
3. **検証**: 全ての文書参照が正しく動作することを確認
4. **Phase 1開始**: カスタムFCO実装（承認後）

---

**作成者**: Claude Code
**最終更新**: 2025-10-11
**ステータス**: 計画策定完了 → 実行準備完了

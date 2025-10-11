# アーカイブ: Boulder LPPLS準拠FCO計画（非推奨）

**アーカイブ日**: 2025-10-11
**理由**: カスタムFCO（過去LPPL準拠）への移行に伴い非推奨

---

## 📋 アーカイブ内容

これらの文書はBoulder LPPLS（外部ライブラリ）準拠のFCO実装計画です。

### アーカイブ済みファイル

- `comparison_fco_vs_current_implementation.md` - Boulder FCO vs 現在実装の比較
- `fco_implementation_gap_analysis.md` - Boulder FCOギャップ分析

---

## ⚠️ 非推奨理由

2025-10-11の調査により、Boulder LPPLSフィッティングでは1987年ブラックマンデーで **0% Confidence** となり、
フィッティングアルゴリズムが収束しないことが判明しました。

**詳細**:
- 時間単位調査: 全時間単位（Index, Ordinal, Normalized）で同じ失敗
- 根本原因: 無制約最適化 + ランダム初期値 → パラメータ発散
- R² = -1006.52（異常値）、A = B = C = 0（収束失敗）

---

## 🎯 新しい移行計画

**カスタムFCO実装（過去LPPL準拠）**を採用します:

- **中心文書**: `docs/progress_management/MIGRATION_PLAN_PAST_LPPL_TO_CUSTOM_FCO.md`
- **科学的差分**: `docs/progress_management/FCO_VS_PAST_LPPL_SCIENTIFIC_DIFFERENCES.md`
- **時間単位調査**: `docs/progress_management/TIME_UNIT_INVESTIGATION_RESULT.md`

**実装方針**:
- 過去LPPL実装（100/100スコア達成）をベースにFCOレベルにアップグレード
- 境界条件付き最適化 + グリッドサーチ初期値戦略
- 時間正規化 [0, 1] + 126窓多重時間窓解析

---

## 🔒 このディレクトリの使用禁止

⚠️ **これらの文書は参照しないでください**

理由:
- カスタムFCO（過去LPPL準拠）に移行するため
- Boulder LPPLS準拠の実装は科学的に不適切（0% Confidence）
- 混乱を避けるためアーカイブ化

---

**アーカイブ担当**: Claude Code
**最終更新**: 2025-10-11
**ステータス**: アーカイブ完了

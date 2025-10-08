# Streamlit Dashboard アーカイブ

**アーカイブ日**: 2025-10-08
**理由**: React + FastAPI アーキテクチャ (FCO v2.1) への移行完了により、Streamlit版は廃止

---

## 📁 アーカイブ文書

### 1. migration_to_react_fastapi.md
- **内容**: Streamlit → React + FastAPI 移行記録
- **作成日**: 2025-09-15
- **参照目的**: 移行時の設計判断・技術的な課題と解決策の記録

### 2. fco_dashboard_requirements.md
- **内容**: Streamlit版 FCO Dashboard 要件定義書
- **作成日**: 2025-09-14
- **参照目的**: FCO v2.0 (Streamlit) 時代の要件・機能仕様の確認

### 3. fco_dashboard_implementation_summary.md
- **内容**: Streamlit版 FCO Dashboard 実装概要
- **作成日**: 2025-09-14
- **参照目的**: Streamlit実装の具体的なコード構造・コンポーネント設計

---

## 🔄 現在の実装

Streamlit版から React + FastAPI 版への移行は完了しました。現在の実装については以下を参照してください：

### React + FastAPI アーキテクチャ (FCO v2.1)

**アーキテクチャ文書**:
- `docs/fco_upgrade_v2/fco_v2.1_architecture.md` - システム全体設計
- `docs/fco_upgrade_v2/technical_implementation_plan.md` - 技術実装詳細

**Dashboard文書** (React版):
- `docs/dashboard_requirements.md` - React Dashboard 要件定義
- `docs/dashboard_implementation_specification.md` - React Dashboard 実装仕様

**FCO機能文書**:
- `docs/fco_upgrade_v2/ds_lppls_indicators_detailed_specification.md` - DS-LPPLS指標仕様
- `docs/fco_upgrade_v2/multi_window_fitting_explanation.md` - 複数窓分析説明

---

## 📚 参照ガイド

### Streamlit版を参照すべき場合

1. **フロントエンド実装の参考**
   - Streamlit版の UI/UX 設計思想
   - インタラクティブ機能の実装パターン
   - データ可視化の手法

2. **移行時の設計判断の理解**
   - なぜ React に移行したか（`migration_to_react_fastapi.md`）
   - Streamlit の制約と React の利点
   - アーキテクチャ選択の根拠

3. **機能要件の確認**
   - FCO v2.0 で実装済みだった機能（`fco_dashboard_requirements.md`）
   - React版での継承・改善すべき機能
   - ユーザー要件の歴史的経緯

### 参照方法

```markdown
<!-- 他の文書からの参照例 -->
Streamlit版の実装については、以下のアーカイブ文書を参照:
- [Streamlit版要件定義](../progress_management/archives/deprecated_streamlit/fco_dashboard_requirements.md)
- [React移行記録](../progress_management/archives/deprecated_streamlit/migration_to_react_fastapi.md)
```

---

## ⚠️ 注意事項

1. **実行不可**: これらの文書に記載された Streamlit コードは現在のシステムでは動作しません
2. **参考目的のみ**: 設計思想・要件理解のための参照用です
3. **将来削除予定**: 参照価値がなくなった時点で完全削除される可能性があります

---

**管理**: docs/progress_management/README.md
**関連アーカイブ**: docs/progress_management/archives/
**最終更新**: 2025-10-08

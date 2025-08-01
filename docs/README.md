# Sornette予測システム ドキュメント

## プロジェクト概要

Didier Sornetteの対数周期パワー法則（LPPL）モデルを実装し、金融市場のクラッシュを予測するシステム。

## ドキュメント構成

### 📊 進捗管理
- [進捗管理システム](./progress_management/) - 現在の進捗とIssue管理
  - [現在の進捗](./progress_management/CURRENT_PROGRESS.md)
  - [アクティブなIssue](./progress_management/CURRENT_ISSUES.md)
  - [管理ガイド](./progress_management/README.md)

### 📚 技術文書
- [数学的基礎](./mathematical_foundation.md) - LPPLモデルの理論と数式
- [実装戦略](./implementation_strategy.md) - システム設計と開発方針
- [論文参照ガイド](./PAPER_REFERENCE_GUIDE.md) - Claude Code用の科学的実装ガイド

### 🗄️ アーカイブ
- [過去の記録](./progress_management/archives/) - 歴史的な進捗とドキュメント

## クイックリンク

- **最優先課題**: β値の再現性問題（目標: 0.33 ± 0.03）
- **現在のフェーズ**: 実装改善（論文再現性の確立）
- **次のマイルストーン**: グローバル最適化手法の導入

## 開発者向け情報

このプロジェクトは生成AI（Claude）との協働を前提として設計されています。進捗管理ファイルは Claude Code が自律的に更新します。

---

*最終更新: 2025-08-01*
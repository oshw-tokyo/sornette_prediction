# 📋 CURRENT ISSUES - アクティブな課題管理

最終更新: 2025-10-08


## 🟡 Active Issues (対応中)

### I122: 🔴 FCO実装の根本的誤り - Nested構造による287倍の過剰計算
**作成日**: 2025-01-15
**優先度**: 🔴 Critical
**担当**: FCOエンジン開発
**状態**: 🚨 緊急対応中

**内容**:
FCO分析エンジン（`core/fitting/fco_engine.py`）が`compute_nested_fits()`を使用しており、FCO標準手法から大きく逸脱。

**問題点**:
1. **Nested構造**: 外側ループ(~287 endpoints)×内側ループ(126 windows) = 約36,162回のフィッティング
2. **FCO標準**: 固定endpoint×126窓 = 126回のフィッティング
3. **処理時間**: 287倍遅い（10日 vs 1時間）
4. **科学的正確性**: FCO標準から完全逸脱
5. **Damping計算式誤り**: `|m|*|ω|/(2π)` ← 正しくは `m*|B|/(ω*|C|)`
6. **全データ無効**: 27期間の解析結果（49,020窓データ）がすべて無効

**影響範囲**:
- `core/fitting/fco_engine.py:136-156` - mp_compute_nested_fits() 呼び出し
- `core/fitting/fco_engine.py:198-199` - Damping計算式誤り
- データベース: SP500の27件の解析結果削除完了（バックアップ済み）

**実施済み対応**:
1. ✅ 実行中の解析プロセス停止（2025-01-15 01:48）
2. ✅ データベースから無効な結果削除（27件＋49,020窓データ）
3. ✅ バックアップ作成（`fco_analysis_results_backup_20251011_015003.db`）

**調査結果** (2025-01-15 02:00):
Boulder LPPLS公式実装との比較完了。主な発見:
1. `compute_nested_fits()`: 時系列分析用（endpointを変化）
2. FCO標準実装には `fit()` メソッドを単純ループで使用すべき
3. 現在の実装はBoulder LPPLSの**誤用**である
4. Damping計算式も独自実装で誤り（Boulder LPPLSに`get_damping()`メソッド存在）

**実装修正完了** (2025-01-15 03:00):
1. ✅ fco_engine.py修正完了: Nested構造→固定endpointループ
2. ✅ Damping計算式修正: FCO標準式 `m*|B|/(ω*|C|)` 実装
3. ✅ 126窓生成テスト成功: 正しく126窓生成確認

**新たな問題発見** (2025-01-15 03:30):
論文再現テスト（1987年ブラックマンデー）で重大な問題を発見:
- **DS-LPPLS Confidence: 0.0%**（期待: >30%）
- **原因**: Boulder LPPLSフィッティングのパラメータ収束問題
- **詳細**:
  - Damping >= 1.0を満たす窓: 2/110 (1.8%)
  - 多くの窓でω < 2.0または tc <= t2（境界条件違反）
  - フィッティング最適化設定の調整が必要

**対応履歴**:
1. ✅ Boulder LPPLS公式実装との詳細比較完了（2025-01-15 02:00）
2. ✅ fco_engine.pyのFCO標準準拠実装への修正（2025-01-15 03:00）
3. ✅ Damping計算式の修正（FCO標準式の実装）（2025-01-15 03:00）
4. ✅ 単体テスト: 126窓が正しく生成されることを確認（2025-01-15 03:00）
5. ✅ 論文再現テスト実行（1987年ブラックマンデー）（2025-01-15 03:30）
6. 🔄 **新Issue I123作成**: Boulder LPPLSフィッティング最適化問題（優先対応）
7. ⏳ 修正版での再解析実行（I123解決後）

**参考資料**:
- FCO標準仕様: `docs/fco_upgrade_v2/foundation/ds_lppls_indicators_detailed_specification.md`
- 実装比較文書: `docs/fco_upgrade_v2/foundation/comparison_fco_vs_current_implementation.md`
- 多重窓解説: `docs/fco_upgrade_v2/foundation/multi_window_fitting_explanation.md`
- Boulder LPPLS: https://github.com/Boulder-Investment-Technologies/lppls

---

### I116: FCO v2.1 Time Series表示問題
**作成日**: 2025-01-15
**優先度**: 高
**担当**: FCO v2.1開発チーム
**状態**: 🔍 調査中

**内容**:
Time Seriesモードでグラフが表示されない問題
- Scatter Viewは修正完了したが、Time Seriesが表示されなくなった
- コンポーネントのレンダリング問題の可能性

**次のアクション**:
1. Time Seriesコンポーネントのデバッグ
2. APIレスポンスとデータ構造の確認
3. Plotlyチャート設定の検証

---

### I117: FCO分析頻度の不整合
**作成日**: 2025-01-15
**優先度**: 高
**担当**: バックエンド開発
**状態**: 📋 計画中

**内容**:
FCO分析の実行頻度に不整合がある
- 最新の2件は1日ごとの解析結果
- それ以前は7日ごとになっている
- 市場が開いている日は毎日分析が必要

**要件**:
- 市場営業日（土日祝日除く）は毎日FCO分析実行
- 過去データのバックフィル実装
- スケジューラーの改善

---

### I118: 個別株データ不足（TSLA, GOOGL）
**作成日**: 2025-01-15
**優先度**: 中
**担当**: データ収集チーム
**状態**: 🔍 調査中

**内容**:
TeslaとGoogleのFCO分析結果が1-2件のみ
- AAPL: 1件のみ
- TSLA: 2件のみ
- GOOGL: 1件のみ
- MSFT: 1件のみ

**推定原因**:
- これらはFRED APIではなくTwelve Data APIを使用
- API制限により十分なデータ取得ができていない可能性
- 価格データ自体は取得できているが、FCO分析が実行されていない

**次のアクション**:
1. 個別株の価格データ取得状況確認
2. FCO分析実行ログの確認
3. APIアクセス制限の見直し

---

### I120: Historical分析での解析済みデータスキップ機能未実装
**作成日**: 2025-10-10
**優先度**: 高
**担当**: バックエンド開発
**状態**: 📋 計画中

**内容**:
Historical分析（`fco-analyze historical`）で解析済みデータのスキップ機能が正しく動作していない
- `force=True`が固定されているため、常に再解析が実行される
- チェック条件が`analysis_date`（実行日時）ベースで、`analysis_basis_date`（分析基準日）ベースではない
- 週次 → 日次切り替え時に、既存の週次データを無駄に再解析する

**影響**:
- 日次解析実行時に約17,808期間すべてを再解析（推定所要時間：約60時間）
- 計算リソースの無駄遣い
- データベースの不要な更新負荷

**必要な修正**:
1. `entry_points/main.py:742`の`force=True`を削除または`--force`オプションで制御
2. `fco_service.py:199-206`のチェック条件を`analysis_basis_date`ベースに変更
3. `FCOResultsDatabase`に`get_analysis_by_date(symbol, analysis_basis_date)`メソッド追加（既存）
4. historical分析ループで各期間の解析前にDB確認処理を追加

**実装例**:
```python
# entry_points/main.py内のhistorical分析ループ
for period_end in periods:
    # 既存分析をチェック
    existing = fco_service.db.get_analysis_by_date(symbol, period_end)
    if existing and not force:
        print(f"  ⏭️  スキップ: {period_end}（既存）")
        continue

    # 新規分析実行
    result = fco_service.run_new_analysis(...)
```

**優先度根拠**:
現在SP500の週次解析実行中（約8.5時間予定）。完了後に日次解析を実行する際、この機能がないと既存の週次データを含む全期間を再解析することになり、時間とリソースの大幅な無駄が発生する。

---

### I119: 全126窓データ保存実装
**作成日**: 2025-10-08
**優先度**: 高
**担当**: FCOバックエンド開発
**状態**: 📋 計画中

**内容**:
FCO分析の全126窓データを保存するシステム実装
- Phase 1: 単一窓データ保存（現状）
- Phase 2: 全126窓データ保存実装
- Phase 3: PostgreSQL移行検討（将来的にデータサイズが大きくなる場合）

**要件**:
- 全窓データの効率的なストレージ設計
- データベーススキーマの拡張
- クエリパフォーマンスの最適化

**依存関係**: FCO v2.1 FastAPIバックエンド完成

---

### I120: 週次→日次用語統一
**作成日**: 2025-10-08
**優先度**: 中
**担当**: ドキュメント管理
**状態**: ✅ 完了（2025-10-08）

**内容**:
システム実装が日次分析であるにも関わらず「週次」と表記されていた文書を修正

**実施内容**:
- 16ファイル・36箇所更新完了
- 用語統一スクリプトの実行
- レポート生成: `workspace_for_claude/weekly_to_daily_update_report.md`

**結果**: ドキュメントとシステム実装の整合性確保

---

### I121: ドキュメント構造最適化
**作成日**: 2025-10-08
**優先度**: 中
**担当**: ドキュメント管理
**状態**: 🔄 進行中

**内容**:
ドキュメントが大きくなりすぎてClaude Codeの認知が難しくなった問題への対応

**作業内容**:
- ✅ workspace_for_claude/のREADME作成（運用ガイドライン）
- ✅ 廃止API文書のアーカイブ移動（Alpha Vantage/CoinGecko）
- ✅ CURRENT_PROGRESS.mdの分割（483→170行）
- 🔄 新規ISSUE追加・古いISSUE整理
- 📋 スケジューラー関連文書の精査
- 📋 大型文書の分割
- 📋 未確認文書の精査
- 📋 アーカイブ文書の取捨選択

**目標**: Claude Codeがプロジェクト全体を効率的に認識できる文書構造の確立

---

### I113: FCO v2.1 チャート実装
**作成日**: 2025-01-15
**優先度**: 高
**担当**: FCO v2.1開発チーム
**状態**: 🚧 実装中

**内容**:
React/Next.jsフロントエンドでのチャートコンポーネント実装
- Rechartsを使用したDS-LPPLS Confidence/Trustグラフ
- リアルタイムデータ更新対応
- レスポンシブデザイン実装

**次のアクション**:
1. ConfidenceChartコンポーネント実装
2. TrustChartコンポーネント実装
3. WebSocket統合によるリアルタイム更新

---

### I114: 認証システム実装
**作成日**: 2025-01-15
**優先度**: 中
**担当**: バックエンド開発
**状態**: 📋 計画中

**内容**:
商用サービス向け認証・認可システムの実装
- JWT Bearer Token認証
- ユーザー管理
- APIレート制限

**依存関係**: I113完了後に着手

---

## 🟢 Resolved Recently (最近解決)

### I115: Scatter View Modeでデータが表示されない問題
**解決日**: 2025-01-15
**問題**: 52件のFCO分析結果中、10件のみ表示される（36件が`bubble_type=None`）
**解決策**:
1. データベースの既存レコードのbubble_typeをFCO公式基準（30%/5%閾値）に基づいて修正
2. predicted_crash_dateがNULLの16件を修正（tc値から計算）、6件の不正データを削除
3. Boulder LPPLSライブラリとの関係性を文書化（コア計算は変更なし、bubble_type判定は適切な拡張）
4. 実運用データフロー検証の必須原則をCLAUDE.mdに追加
**結果**: 46件のデータポイントが正常に表示されるように改善（FCO基準準拠、異常なプロット位置の解消）

### I112-1: シンボル名表示バグ
**解決日**: 2025-01-15
**問題**: APIがオブジェクトではなく文字列配列を返していた
**解決策**: `get_available_symbols()`を修正し、`{symbol, name}`形式のオブジェクトを返すように変更

### I112-2: データベースパス問題
**解決日**: 2025-01-15
**問題**: ハードコードされた絶対パスによる環境依存
**解決策**: `pathlib.Path(__file__)`を使用した相対パス解決実装

---

## 📊 Issue Statistics

- **Total Active Issues**: 8
- **Critical**: 0
- **High Priority**: 4 (I116, I117, I119, I113)
- **Medium Priority**: 3 (I118, I114, I121)
- **Low Priority**: 0
- **Recently Completed**: 1 (I120)

---

## 🔄 Issue Lifecycle

1. **作成**: 問題発見時に即座に記録
2. **優先度設定**: Critical/High/Medium/Low
3. **担当割当**: 適切なチームメンバーへ
4. **対応**: 実装・テスト・検証
5. **解決**: 完了後、Resolved Recentlyへ移動
6. **アーカイブ**: 1ヶ月後に別ファイルへ

---

## 🏷️ Labels

- 🔴 **Critical**: システム停止・データ損失リスク
- 🟠 **High**: 主要機能の障害
- 🟡 **Medium**: 副次機能の問題
- 🟢 **Low**: 改善提案・最適化

---

## 📝 Notes

- 古いStreamlit実装関連のissueは削除済み（FCO v2.1移行により不要）
- FCO v2.0のダッシュボード関連issueは解決済みとしてアーカイブ
- 今後はReact+FastAPIアーキテクチャに関連するissueを管理

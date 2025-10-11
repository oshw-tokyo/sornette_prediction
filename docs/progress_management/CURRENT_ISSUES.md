# 📋 CURRENT ISSUES - アクティブな課題管理

最終更新: 2025-10-08


## 🟡 Active Issues (対応中)

### I122: 🔴 FCO実装の根本的誤り - Nested構造による287倍の過剰計算
**作成日**: 2025-01-15
**解決日**: 2025-10-11
**優先度**: 🔴 Critical
**担当**: FCOエンジン開発
**状態**: ✅ 解決済み（Issue I123へ移行）

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
6. ✅ Log変換バグ修正 + データベースフォールバック実装（2025-10-11 02:00）
7. ✅ 保護的コメント追加（Boulder LPPLS依存関係明示）（2025-10-11 02:30）
8. ✅ Git commit & GitHub push完了（2025-10-11 03:00）
9. 🔄 **Issue I123作成**: Boulder LPPLSフィッティング最適化問題（次の優先対応）

**解決サマリー（2025-10-11）**:
- ✅ Nested構造を廃止し、FCO標準の固定endpointループに修正
- ✅ Damping計算式をFCO標準式に修正
- ✅ Log変換の自動判定機能を実装
- ✅ データベースフォールバック機能を実装
- ✅ 126窓が正しく生成されることを確認
- ✅ 実装構造がFCO標準に準拠することを確認
- ⏳ 1987年検証: Confidence=0%（Issue I123で対応）

**Git Commit**: `02a129e` - "🔧 Fix critical FCO implementation errors (Issue I122)"

**参考資料**:
- FCO標準仕様: `docs/fco_upgrade_v2/foundation/ds_lppls_indicators_detailed_specification.md`
- 実装比較文書: `docs/fco_upgrade_v2/foundation/comparison_fco_vs_current_implementation.md`
- 多重窓解説: `docs/fco_upgrade_v2/foundation/multi_window_fitting_explanation.md`
- Boulder LPPLS: https://github.com/Boulder-Investment-Technologies/lppls

---

### I124: 🔴 FCO実装の正確性検証とDamping閾値問題
**作成日**: 2025-10-11
**優先度**: 🔴 Critical（最優先）
**担当**: FCOエンジン開発
**状態**: 🔍 調査完了 → 🧪 実験フェーズ
**前提**: Issue I122解決済み、Issue I123要再検討

**内容**:
FCO本家・Boulder LPPLS・本実装の関係を徹底調査した結果、以下が判明：

**調査結果サマリー**:
1. ✅ **Issue I122修正は正しかった**
   - 本実装はFCO月次レポートの「1回の分析」（固定t2、126窓）を正しく実装
   - Boulder `compute_nested_fits()`は時系列追跡用（目的が異なる）

2. ✅ **Boulder LPPLSは正しく利用されている**
   - 公式パッケージ（v0.6.20）として使用
   - ローカル変更なし
   - `fit()`メソッドの直接呼び出し = 正しい使用法

3. ⚠️ **0% Confidenceの真因: Damping閾値**
   - **Boulder標準**: Damping >= 0.5
   - **本実装**: Damping >= 1.0 ← **厳しすぎる可能性**
   - 1987年データ: Damping >= 1.0 を満たすのは1.8%のみ

**重要な発見**:

| 項目 | Boulder LPPLSデフォルト | 本プロジェクト実装 |
|------|------------------------|------------------|
| Damping閾値 | 0.5 | 1.0 |
| m範囲 | 0.0 - 1.0 | 0.1 - 0.9 |
| ω範囲 | 2.0 - 15.0 | 2.0 - 25.0 |

**実験計画**:
1. Damping閾値を0.5に緩和して1987年検証
2. フィルタリング条件の段階的緩和テスト
3. Boulder標準実装（`compute_indicators()`）との比較

**次のアクション**:
1. `fco_engine.py:202` のDamping閾値を0.5に変更
2. 1987年ブラックマンデー検証を再実行
3. Confidence > 0%になることを確認
4. 最適な閾値を決定

**詳細ドキュメント**:
`docs/progress_management/ISSUE_I124_FCO_IMPLEMENTATION_VERIFICATION.md`

---

### I123: 🟡 Boulder LPPLSフィッティング最適化パラメータ調整
**作成日**: 2025-10-11
**優先度**: 🟡 Medium（要再検討）
**担当**: FCOエンジン開発
**状態**: ⏸️ 保留中（Issue I124完了後に再評価）
**前提**: Issue I122解決済み（実装構造はFCO標準準拠）

**内容**（要再評価）:
FCO実装構造の修正後も、1987年ブラックマンデー検証でDS-LPPLS Confidence=0%となる。
実装構造は正しいが、Boulder LPPLSのフィッティング最適化パラメータが適切に収束していない。

**Issue I124調査結果による再評価**:
- Boulder LPPLSの初期値設定は**すでに実装済み**（ランダム初期値 + 25回リトライ）
- 本Issueで提案した「最適化パラメータ調整」は、FCO方法論として**すでに標準実装されている**可能性が高い
- 0% Confidenceの真因は**Damping閾値**（Issue I124で対応中）

**再評価後の位置づけ**:
- ❌ 「新機能実装」ではない
- ✅ 「パラメータ調整」として有効
- Issue I124完了後、必要に応じて初期値範囲の調整を検討

**問題の詳細**:
- **DS-LPPLS Confidence**: 0.0%（期待: >30%）
- **実装構造**: ✅ 正常（126窓、固定endpoint、FCO標準Damping式）
- **データ**: ✅ 正常（1971-1988年、1000日分）
- **根本原因**: Boulder LPPLS `fit()`の最適化パラメータが不適切

**統計データ（1987年データでの分析）**:
```
総窓数: 110窓（データ不足により一部窓がスキップ）
適格フィット: 0窓

FCOフィルタリング条件達成率:
- Damping >= 1.0:        2/110 (1.8%)  ← **最大のボトルネック**
- 0.1 <= m <= 0.9:       53/110 (48%)
- 2.0 <= ω <= 25.0:      101/110 (92%)
- tc > t2（未来のtc）:   68/110 (62%)
```

**原因分析**:
1. **Dampingが極端に小さい**: 大多数の窓でdamping < 0.5
   - FCO基準（>= 1.0）を満たすのは1.8%のみ
2. **ωが小さすぎる**: 一部の窓でω < 2.0（境界条件違反）
3. **tcが過去**: 約38%の窓でtc <= t2（過去のtc）

これらはBoulder LPPLS `fit()`の最適化が局所解に陥っていることを示唆。

**Boulder LPPLS `fit()`パラメータ（現在の設定）**:
```python
lppls_model.fit(
    max_searches=25,
    minimizer='Nelder-Mead',
    obs=window_observations
)
```

**調整候補**:
1. **max_searches**: 25 → 50-100（探索回数を増やす）
2. **minimizer**: 'Nelder-Mead' → 他のアルゴリズム検討
   - 'L-BFGS-B'（勾配ベース）
   - 'Powell'
   - 'SLSQP'（制約付き最適化）
3. **初期値・境界条件**: Boulder LPPLSのデフォルト値を調査・調整
4. **フィッティング前処理**: データ正規化・スケーリング

**次のアクション**:
1. Boulder LPPLSのドキュメント・コードを精査し、最適化パラメータの推奨設定を確認
2. 異なるminimizerアルゴリズムでのテスト実行
3. max_searchesを段階的に増やしてテスト
4. 初期値・境界条件の調整を検討
5. 1987年データで再検証

**重要な注意事項**:
⚠️ Boulder LPPLSのコアロジックは変更しない（MIT License準拠）
⚠️ パラメータ調整のみで対応
⚠️ 調整後は必ず論文再現テストで検証

**調査ファイル**:
- `workspace_for_claude/debug_fco_1987_fits_output.txt` - 詳細な窓別分析結果
- `workspace_for_claude/debug_fco_1987_fits.py` - デバッグスクリプト

**参考資料**:
- Boulder LPPLS: https://github.com/Boulder-Investment-Technologies/lppls
- Boulder LPPLS Examples: https://github.com/Boulder-Investment-Technologies/lppls/tree/master/examples

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

### I125: フィッティング条件の透明性・再現性確保
**作成日**: 2025-10-11
**優先度**: 🔴 Critical（商用サービス化要件）
**担当**: フロントエンド開発 + ドキュメント管理
**状態**: 📋 計画中

**内容**:
ユーザーがフィッティング条件を確認し、結果を再現できる情報を公開する必要がある。

**要件**:
1. **使用理論の明示**:
   - Sornette LPPL理論（Log-Periodic Power Law）
   - 論文引用: Sornette et al. (2004), Johansen & Sornette (2001)
   - 理論の数学的定義

2. **フィッティングコードの公開**:
   - コア実装の個別公開（GitHubパッケージ化）
   - `core/fitting/lppl_optimizer.py`
   - `core/fitting/lppl_utils.py`
   - ライセンス: MIT（検討中）

3. **初期パラメータの公開**:
   - グリッドサーチ範囲: tc∈[1.01, 1.5], beta∈[0.30, 0.45], omega∈[5.0, 8.0]
   - 試行回数: n_tries=10 → 10³=1000組み合わせ
   - 最適化手法: Trust Region Reflective (scipy.optimize.curve_fit)

4. **パラメータ許容範囲の公開**:
   - tc: [1.01, 1.5]（**tc > 1.0 必須：未来予測限定**）
   - beta: [0.3, 0.7]
   - omega: [5.0, 8.0]
   - phi: [-8π, 8π]
   - A, B, C: [-10, 10], [-10, 10], [-2.0, 2.0]

5. **制約条件の説明**:
   - **tc > 1.0**: 未来のクラッシュ予測に限定（Sornette理論準拠）
   - **30～60日制約**: フィッティング基準日はクラッシュ予測日の30～60日前（Sornette論文準拠）
   - **理由**: クラッシュ付近では関数の数値変動が大きく、正しいフィッティングが困難

6. **再現性確保**:
   - データ期間の明示
   - フィッティング基準日の明示
   - 使用データソース（FRED等）
   - 完全な実行手順

**フロントエンド実装（React UI）**:
1. **"Methodology" タブ**:
   - 理論の説明
   - 数式の表示（LaTeX）
   - 論文引用・リンク

2. **"Parameters" タブ**:
   - 初期値・境界条件の表示
   - 制約条件の説明
   - 各パラメータの意味

3. **"Reproduce" タブ**:
   - GitHubリポジトリリンク
   - 実行手順
   - サンプルコード

4. **各分析結果に以下を表示**:
   - フィッティング基準日
   - 使用データ期間
   - フィッティング条件（tc > 1.0等）

**コード公開範囲（検討中）**:
- ✅ LPPLフィッティング実装（core/fitting/）
- ✅ LPPL数式実装（lppl_utils.py）
- ❓ FCO多重窓実装（商用差別化要素として検討）

**Sornette論文の30～60日制約**:
- 論文根拠を確認中（papers/extracted_texts/内）
- 歴史的クラッシュ再現テストでは60日前基準を採用
- コード内に科学的根拠コメントを追加

**依存Issue**:
- Phase 2実装後に対応（現在Phase 1完了）
- FCO v2.1 React UIと統合

**参考文書**:
- `docs/mathematical_foundation.md` - LPPL理論
- `CLAUDE.md` - tc > 1.0条件の説明
- `docs/progress_management/CRITICAL_FINDING_data_period_impact.md` - データ期間の影響

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

### I127: 🟡 カスタムFCOパフォーマンス最適化（マルチプロセッシング並列化）
**作成日**: 2025-10-11
**完了日**: 2025-10-12
**優先度**: 🟡 Medium（Phase 2完了後の最適化）
**担当**: カスタムFCO開発
**状態**: ✅ 完了（並列化実装成功、科学的精度100%保証）

**内容**:
カスタムFCO多重窓解析のパフォーマンス最適化。現在は逐次実行（シングルスレッド）のため、マルチコアCPUの計算リソースを活用できていない。

**Phase 2検証結果（2025-10-11）**:
- ✅ DS-LPPLS Confidence: 41.18% （目標>30%達成）
- ✅ 予測誤差: 20日 （目標≤60日達成）
- ✅ 51窓（250-750日）: 約5-7分
- ⚠️ FCO標準126窓: 推定60-90分（未最適化）

**実装完了（2025-10-12）**:
- ✅ `compute_ds_lppls_confidence_parallel()` メソッド実装
- ✅ multiprocessing.Pool による並列実行
- ✅ 科学的精度100%保証（全テストPASS）
- ✅ 2.86倍高速化達成（70.82秒 → 24.78秒、7ワーカー）

**ボトルネック分析**:
1. **CPU並列化未使用** ⭐⭐⭐（最優先）
   - 現状: 全窓を逐次実行（シングルスレッド）
   - 影響: 8コアで理論上8倍高速化可能
   - 解決策: Python `multiprocessing`モジュール使用

2. **小窓（<250日）の収束失敗**
   - 現状: 125-250日の窓で全グリッドサーチ失敗
   - 影響: 計算リソースの無駄
   - 解決策: 実用的最小窓サイズ250日（実装済み）

**提案1: マルチプロセッシング並列化（最優先）**
```python
from multiprocessing import Pool, cpu_count

def compute_ds_lppls_confidence_parallel(self, prices, n_workers=None):
    if n_workers is None:
        n_workers = cpu_count() - 1  # 1コアはOSに残す

    window_sizes = list(range(self.WINDOW_MIN, self.WINDOW_MAX + 1, self.WINDOW_STEP))

    # 各窓のパラメータを準備
    window_params = [(prices[-ws:], self.n_tries, ws) for ws in window_sizes]

    # 並列実行
    with Pool(n_workers) as pool:
        window_results = pool.starmap(
            self._fit_single_window_worker,
            window_params
        )

    return self._aggregate_results(window_results)
```

**性能測定結果（2025-10-12）**:
| 項目 | 逐次版 | 並列版（7ワーカー） | 高速化率 |
|------|--------|-------------------|----------|
| **実行時間** | 70.82秒 | 24.78秒 | 2.86倍 ⭐ |
| **時間短縮** | - | 46.05秒 | 65.0% |
| **DS-LPPLS Confidence** | 54.55% | 54.55% | ✅ 完全一致 |
| **適格フィット数** | 6/11 | 6/11 | ✅ 完全一致 |
| **予測tc** | 1.1646 | 1.1646 | ✅ 完全一致 |
| **全窓結果** | - | - | ✅ 完全一致 |

**科学的精度保証テスト（全テストPASS）**:
1. ✅ DS-LPPLS Confidence一致（差分 < 1e-10）
2. ✅ 適格フィット数一致
3. ✅ 予測tc一致（差分 0.00e+00）
4. ✅ 全窓のパラメータ一致（R², beta, omega, tc）

**実装詳細**:
- **ファイル**: `core/fitting/custom_fco_engine.py`
- **新規メソッド**: `compute_ds_lppls_confidence_parallel()`
- **静的ワーカー関数**: `_fit_single_window_worker_static()`, `_apply_filtering_static()`
- **使用ライブラリ**: Python標準ライブラリ（multiprocessing）
- **依存関係追加**: なし（既存のPython標準モジュールのみ）

**実装方針**:
- ✅ 既存メソッドは一切変更せず（後方互換性100%）
- ✅ 新しい並列版メソッドを追加（オプトイン方式）
- ✅ シンプルで管理しやすい実装
- ✅ 詳細なコメント（科学的精度保証の説明）
- ✅ 計測機能内蔵（elapsed_time_secをmetadataに記録）

**テストファイル**:
`workspace_for_claude/test_parallel_performance.py`

**詳細ドキュメント**:
- `workspace_for_claude/performance_optimization_investigation.md`
- `core/fitting/custom_fco_engine.py` - 実装コード＋詳細コメント

**今後の展開**:
- ✅ 並列化実装完了
- 📋 Phase 3（データベース・フロントエンド統合）で並列版採用を検討
- 📋 フル126窓での性能測定（推定：60-90分 → 20-30分）

---

### I126: 🔴 境界張り付き時のConfidence計算方法（FCO本家準拠確認）
**作成日**: 2025-10-11
**優先度**: 🔴 Critical（Phase 1実装の前提条件）
**担当**: カスタムFCO開発
**状態**: ✅ 解決済み（Phase 2実装で安全側方式採用）

**内容**:
カスタムFCO実装において、パラメータが境界値に張り付いたフィッティングをDS-LPPLS Confidence計算にどう扱うべきか、方針が不明確。

**背景**:
- **ユーザーフィードバック（a）**: 「信頼性を担保するなら、安全側で失敗した結果としてConfidenceに含める方がよい」
- **初期実装案**: 境界張り付きを適格フィット から除外（Confidence計算に含めない）
- **懸念**: FCO本家でどう扱われていたか不明

**調査項目**:
1. **FCO本家実装の確認**:
   - Boulder LPPLS公式リポジトリの`compute_indicators()`メソッドを精査
   - 境界張り付き判定の有無と処理方法
   - Confidence計算における除外/含める基準

2. **理論的根拠の調査**:
   - FCO論文での記述確認
   - Sornette論文での境界条件の取り扱い
   - tc過去指定との関連性（過去tcを許容する理由がConfidence計算の一貫性の可能性）

3. **両方式の影響分析**:
   - **除外方式**: 適格フィット率のみで計算（厳しい基準）
   - **含める方式**: 失敗フィットも分母に含める（安全側、保守的）
   - 1987年データでの試算比較

**暫定方針（ユーザー指示）**:
✅ **安全側実装を採用**
- 境界張り付きのフィットは「失敗」として扱う
- **Confidence計算には含める**（分母にカウント、分子には含めない）
- 計算式: `Confidence = 適格フィット数 / 総窓数 × 100`
  - 総窓数: 境界張り付き含む全フィッティング試行
  - 適格フィット数: 境界張り付きを除外

**実装への影響**:
```python
# Phase 2実装（多重窓FCO）での計算方法
total_windows = 126  # 全窓数
qualified_fits = 0   # 適格フィット数
boundary_adhesions = 0  # 境界張り付き数

for window in windows:
    result = fit_lppl_grid_search(...)

    # 境界張り付きチェック
    if check_boundary_adhesion(result):
        boundary_adhesions += 1
        # 含める方式: 失敗としてカウント（適格フィットには含めない）
        continue  # 適格フィット数には加算しない

    # その他のフィルタリング条件
    if passes_fco_filters(result):
        qualified_fits += 1

# Confidence計算
confidence = (qualified_fits / total_windows) * 100
```

**FCO本家確認後の対応**:
1. Boulder LPPLSの`compute_indicators()`実装を精査
2. 境界張り付き判定の有無・処理方法を確認
3. 必要に応じて実装方針を調整
4. 調査結果を本Issueに追記
5. 最終的な実装方針を決定

**参考資料**:
- Boulder LPPLS: https://github.com/Boulder-Investment-Technologies/lppls
- FCO論文: `papers/extracted_texts/` 内
- 実装コード: `core/fitting/lppl_optimizer.py`

**次のアクション**:
1. Boulder LPPLSの`lppls/lppls.py`内の`compute_indicators()`メソッドを詳細調査
2. フィルタリング条件の実装を確認
3. 境界張り付き判定の有無を確認
4. Phase 1実装前に調査結果を報告

**関連Issue**:
- Issue I124: FCO実装の正確性検証（Damping閾値問題）
- Issue I125: フィッティング条件の透明性・再現性確保

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

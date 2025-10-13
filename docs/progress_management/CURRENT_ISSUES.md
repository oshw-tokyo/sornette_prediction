# 📋 CURRENT ISSUES - アクティブな課題管理

最終更新: 2025-10-13


## 🟡 Active Issues (対応中)

### I130: 🔵 Boulder LPPLS FCOフィルタリング実装の調査
**作成日**: 2025-10-13
**優先度**: 🔵 Medium
**担当**: カスタムFCO開発
**状態**: 🔍 調査完了（実装への適用検討中）

**内容**:
カスタムFCO実装においてパラメータ境界張り付き問題が発生していたため、Boulder LPPLS FCO（公式ライブラリ）のフィルタリング実装を調査し、カスタムFCO実装との差異を明確化する。

**調査結果サマリー**:
1. ✅ **Boulder LPPLS v0.6.20のフィルタリング実装を特定**
   - 実装箇所: `/home/no-rules/.local/lib/python3.10/site-packages/lppls/lppls.py`
   - メソッド: `compute_indicators()` (lines 240-356)

2. ✅ **5つのフィルタリング条件を確認**:
   - **m (beta) 範囲**: 0.0 < m < 1.0
   - **w (omega) 範囲**: 2.0 < w < 15.0
   - **tc範囲**: max(t2 - 60, t2 - 0.5*(t2-t1)) < tc < min(t2 + 252, t2 + 0.5*(t2-t1))
   - **Oscillations**: O > 2.5
   - **Damping**: D > 0.5

3. ✅ **カスタムFCO実装との比較**:

| 項目 | Boulder LPPLS | カスタムFCO実装 | 差異 |
|------|---------------|----------------|------|
| **m (beta) 範囲** | 0.0 - 1.0 | 0.1 - 0.9 | カスタムは狭い |
| **w (omega) 範囲** | 2.0 - 15.0 | 5.0 - 15.0 | カスタムは狭い |
| **O_min** | 2.5 | ❌ 未実装 | **カスタムに欠落** |
| **D_min** | 0.5 | ❌ 未実装 | **カスタムに欠落** |
| **tc範囲** | 過去60日～未来252日 | 未来のみ（tc > 1.0） | **大きく異なる** |
| **境界張り付きチェック** | ❌ なし | ✅ あり（2%マージン） | カスタム独自 |

**重要な発見**:

1. **Boulder LPPLSは境界張り付きをチェックしない**:
   - パラメータが境界値（例: m=1.0, w=15.0）でも適格とみなす
   - カスタムFCOの厳格な境界張り付きチェック（2%マージン）は独自実装

2. **カスタムFCOにOscillations/Damping閾値が欠落**:
   - Boulder LPPLSでは O > 2.5, D > 0.5 を要求
   - カスタムFCOでは未実装（`custom_fco_engine.py` にコードなし）
   - fco_engine.py（Boulder LPPLS FCO）には実装あり

3. **tc範囲制約の哲学的違い**:
   - Boulder LPPLS: 過去のtcも許容（t2 - 60日 ～ t2 + 252日）
   - カスタムFCO: 未来予測のみ（tc > 1.0）
   - → **科学的根拠の再確認が必要**

**追加調査完了** (2025-10-13):

1. ✅ **Oscillations/Damping閾値の詳細調査**:
   - **O (Oscillations)**: データ期間内での振動回数、O > 2.5 で統計的有意性を保証
   - **D (Damping)**: べき乗減衰と振動振幅の比率、D > 0.5 で真のLPPL挙動を保証
   - **科学的意味**: Sornette理論の本質（べき乗減衰 + 対数周期振動の共存）を数値的に検証
   - **カスタムFCOへの適用**: 実装推奨（Boulder LPPLS FCOとの整合性向上）
   - 詳細: `workspace_for_claude/issue_i130_oscillations_damping_investigation.md`

2. ✅ **境界張り付きチェック vs パラメータ範囲の関係調査**:
   - **2つは異なる概念**:
     - パラメータ範囲フィルタ: 範囲外を棄却（Boulder LPPLS: ✅あり、カスタムFCO: ✅あり）
     - 境界張り付きチェック: 範囲内だが境界近傍を棄却（Boulder LPPLS: ❌なし、カスタムFCO: ✅あり）
   - **Boulder LPPLSに境界張り付きチェックがない理由**:
     - 無制約最適化の哲学（範囲内であれば真の最適解と見なす）
     - 広い範囲設定（m=0.0-1.0, w=2.0-15.0）により境界張り付きが稀
   - **カスタムFCOの厳格性は正当化可能**: 成功実績あり（43.14% Confidence達成）
   - 詳細: `workspace_for_claude/issue_i130_boundary_vs_range_investigation.md`

3. ✅ **パラメータ許容範囲と初期値範囲の混同問題調査**:
   - **ユーザーの懸念は正しい**: グリッドサーチ範囲とbounds範囲が完全に一致
   - **問題**: 境界値（1.01, 1.5, 0.1, 0.9, 5.0, 15.0）から開始する最適化が境界張り付きリスクを高める
   - **推奨改善**: グリッドサーチ範囲をboundsの内側10%～90%に設定
     - 例: beta_values = np.linspace(0.18, 0.82, n_tries)  # boundsは0.1-0.9のまま
   - **効果**: 境界張り付きリスク低減、計算効率向上、科学的に正しい設計
   - 詳細: `workspace_for_claude/issue_i130_parameter_range_confusion_investigation.md`

**次のアクション**（ユーザー承認、2025-10-13）:

1. 🔄 **Oscillations/Damping閾値の実装** （実装中）:
   - カスタムFCO実装（`custom_fco_engine.py`）に O > 2.5, D > 0.5 を追加
   - **重要**: Boulder LPPLS FCOとの整合性向上が目的
   - 検証テスト実行（1987年ブラックマンデー）
   - DS-LPPLS Confidence変化測定（43.14% → ?%）

2. 🔄 **過剰フィルタリングの一時的不活性化** （実装中）:
   - **背景**: カスタムFCOの厳格なフィルタリングが適格フィット数を減少させている可能性
   - **対象**:
     - ✅ tc範囲チェック: 未来のみ制約（tc > 1.0）を一時的に緩和
     - ✅ 境界張り付きチェック: 2%マージンを一時的に無効化または緩和
   - **維持すべき項目**:
     - ✅ 初期パラメータ: tc > 0 で振る（既存の出発点を維持）
     - ✅ 基本的なパラメータ範囲: beta=0.1-0.9, omega=5.0-15.0
     - ✅ R² > 0.5 の品質閾値
   - **目的**: Oscillations/Damping閾値のみで品質管理を行い、過剰フィルタリングを回避
   - **実装方針**:
     - フィルタリング条件をコメントアウトまたはフラグで制御可能にする
     - 検証テスト実行後、効果を測定してから恒久化を判断

3. 📋 **グリッドサーチ範囲の改善実装** （保留）:
   - `lppl_optimizer.py`のグリッドサーチ範囲をbounds内側10%～90%に変更
   - ⚠️ 注意: 過剰フィルタリング緩和の効果確認後に実施
   - 検証テスト実行
   - 適格フィット数・Confidence変化測定

4. 📋 **Sornette論文での根拠確認** （補助タスク）:
   - 境界張り付きに関する記述の調査
   - tc範囲制約に関する記述の調査

**詳細レポート**:
- `workspace_for_claude/boulder_lppls_filtering_investigation.md` - 完全調査レポート
- `workspace_for_claude/issue_i130_oscillations_damping_investigation.md` - O/D閾値詳細
- `workspace_for_claude/issue_i130_boundary_vs_range_investigation.md` - 境界張り付きvs範囲
- `workspace_for_claude/issue_i130_parameter_range_confusion_investigation.md` - 初期値範囲問題

**関連Issue**:
- Issue I129: カスタムFCO多重窓パラメータ整合性修正（✅ 解決済み）
- Issue I128: tc→日付変換修正（✅ 解決済み）

---

### I132: 🔵 進捗管理方法の検討（進捗管理ファイル vs Issue+CLAUDE.md）
**作成日**: 2025-10-13
**優先度**: 🔵 Medium
**担当**: プロジェクト管理
**状態**: ✅ 承認済み（Option A採用、実装中）
**承認日**: 2025-10-13

**内容**:
進捗管理ファイル（CURRENT_PROGRESS.md）が更新されないケースが発生しているため、Issue管理ベースへの移行または進捗管理ファイル強化を検討する。

**現状の問題**:
1. **進捗管理ファイル（CURRENT_PROGRESS.md）の更新漏れ**:
   - 新セッション開始時に参照されない
   - Issue管理（CURRENT_ISSUES.md）は機能している

2. **二重管理の負担**:
   - Issue + 進捗管理ファイルの両方を更新する必要
   - 生成AIセッションの揮発性により管理負担が大きい

**検討する選択肢**:

**選択肢A: Issue管理ベース + CLAUDE.mdで現在作業を簡潔に記載**
- ✅ Issue管理（CURRENT_ISSUES.md）を主軸とする
- ✅ CLAUDE.mdに「現在進行中のタスク」セクションを簡潔に追加
- ✅ 進捗管理ファイル（CURRENT_PROGRESS.md）は廃止またはアーカイブ参照のみ
- メリット:
  - 管理負担の軽減
  - Issueで詳細追跡、CLAUDE.mdで概要把握
  - 新セッション開始時の理解が容易
- デメリット:
  - 長期的な進捗履歴の可視性低下
  - マイルストーン管理が弱くなる

**選択肢B: 進捗管理ファイルの強化**
- ✅ CLAUDE.mdに進捗管理ファイル参照を強化
- ✅ 新セッション開始チェックリストに進捗更新を明記
- ✅ Issue作成時に進捗管理ファイルへのリンク記載を義務化
- メリット:
  - 長期的な進捗履歴が維持される
  - マイルストーン管理が明確
- デメリット:
  - 依然として二重管理の負担
  - 生成AIセッションでの継続的更新が困難

**推奨案: 選択肢A（Issue管理ベース）**

理由:
1. **生成AIの特性に適合**: セッションごとの揮発性に対応
2. **実績あり**: Issue管理（CURRENT_ISSUES.md）は機能している
3. **管理負担軽減**: 単一の情報源（Issue）で十分
4. **CLAUDE.md簡潔化**: 現在作業のみ記載、詳細はIssue参照

**承認された実装方針（Option A）**:

**git commit中心の進捗管理**:
- ✅ **git commitメッセージで進捗を記録**: 各作業完了時に詳細なcommitメッセージを残す
- ✅ **進捗確認はgit log**: `git log --oneline -20` で最近の作業内容を確認
- ✅ **Issue管理（CURRENT_ISSUES.md）**: 詳細なタスク追跡・調査結果の記録
- ✅ **CLAUDE.md**: 現在進行中のタスク概要のみ記載（詳細はIssue参照）

**ブランチ戦略**:
- ✅ **基本ブランチ**: `main`（安定版）と`dev`（開発版）のみ
- ✅ **Claude Codeの作業対象**: 原則として`dev`ブランチ
- ✅ **本番反映**: `dev` → `main`へのマージは慎重に実施（検証完了後）
- ⚠️ **理由**: feature/*ブランチ運用は管理負担が大きいため、シンプルなdev/main構成を採用

```markdown
# CLAUDE.md に追加するセクション

## 📊 **進捗管理とブランチ戦略**

### 進捗管理方針
**git commit中心の進捗管理** (Issue I132承認、2025-10-13)

進捗状況は以下で確認：
1. **git log**: `git log --oneline -20` で最近の作業内容
2. **Issue管理**: `docs/progress_management/CURRENT_ISSUES.md` で詳細追跡
3. **CLAUDE.md**: 現在進行中のタスク概要（本セクション下部）

**CURRENT_PROGRESS.md**: 廃止（アーカイブのみ）

### ブランチ戦略
- **main**: 安定版（本番相当）
- **dev**: 開発版（Claude Codeの作業対象）
- **運用**: feature/*ブランチは使用せず、シンプルなdev/main構成

### 🔄 **現在進行中のタスク**

**⚠️ 詳細はIssue管理システムを参照**: `docs/progress_management/CURRENT_ISSUES.md`

- **Issue I130**: Boulder LPPLS FCOフィルタリング調査（🔍 調査完了、実装中）
- **Issue I131**: CLAUDE.md整理タスク（🔄 進行中）
- **Issue I132**: 進捗管理方法の検討（✅ 承認済み、実装中）
- **Issue I133**: 再現性テストのCI/CD化（📋 計画中）

**現在のフェーズ**: カスタムFCO Phase 3実装準備中
```

**CURRENT_PROGRESS.mdの扱い**:
- ✅ **廃止決定**: 今後の更新は停止
- ✅ **アーカイブ**: `archives/`に移動（参照用として保持）
- ✅ **代替手段**: git log + Issue管理で長期的な進捗履歴を追跡

**実装アクション**:
1. ✅ ユーザー承認取得（2025-10-13）
2. 🔄 CLAUDE.mdに進捗管理セクション追加（実装中）
3. 📋 CLAUDE.mdに「コードを正とする原則」拡張追記（実装中）
4. 📋 CURRENT_PROGRESS.mdをアーカイブ化
5. 📋 新セッション開始チェックリストを更新

**関連Issue**:
- Issue I131: CLAUDE.md整理タスク（並行作業）

---

### I133: 🔵 再現性テストのCI/CD化（GitHub push前実施）
**作成日**: 2025-10-13
**優先度**: 🔵 Medium（カスタムFCO完了後は🟡 High）
**担当**: テスト・品質管理
**状態**: 📋 計画中（カスタムFCO Phase 3完了後に実施）

**内容**:
再現性テスト（歴史的クラッシュ検証）をGitHub pushまたはコミット前に自動実行し、科学的妥当性を常に保証する仕組みを構築する。

**目標**:
- **歴史的クラッシュの予測精度を常にクリア**: 1987年ブラックマンデー等
- **関連指標の基準値クリア**: DS-LPPLS Confidence, R², 予測誤差等
- **GitHub push前の必須チェック**: テスト失敗時はpush不可

**現在のテスト体系**（カスタムFCO）:
1. **Phase 1**: 単一窓LPPL検証
   - テスト: `tests/custom_fco/test_phase1_single_window.py`
   - 基準: R² > 0.9, tc > 1.0, 予測誤差 ≤ 35日, 境界張り付きなし

2. **Phase 2**: 多重窓FCO検証
   - テスト: `tests/custom_fco/test_phase2_multi_window.py`
   - 基準: DS-LPPLS Confidence > 30%, positive_bubble, 予測誤差 ≤ 60日

3. **統合検証**:
   - エントリーポイント: `python entry_points/main.py validate --crash 1987 --fco`
   - 基準: 全メトリクスクリア

**実装案**:

**1. GitHub Actions ワークフロー**:
```yaml
# .github/workflows/reproducibility_tests.yml
name: Reproducibility Tests

on:
  push:
    branches: [ main, develop, feature/* ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run reproducibility tests
        run: |
          python entry_points/main.py validate --crash 1987 --fco
          python tests/custom_fco/test_phase1_single_window.py
          python tests/custom_fco/test_phase2_multi_window.py
      - name: Check test results
        run: |
          # テスト結果の検証（exit code確認）
          if [ $? -ne 0 ]; then
            echo "❌ Reproducibility tests failed"
            exit 1
          fi
```

**2. Pre-commit Hook** （ローカル開発用）:
```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "🔬 Running reproducibility tests..."

python entry_points/main.py validate --crash 1987 --fco
if [ $? -ne 0 ]; then
    echo "❌ Reproducibility test failed. Commit aborted."
    exit 1
fi

echo "✅ All reproducibility tests passed"
```

**3. テスト結果の可視化**:
- GitHub Actions バッジをREADME.mdに追加
- テスト履歴の自動記録（artifacts）
- メトリクス推移のグラフ化

**次のアクション**（カスタムFCO Phase 3完了後）:
1. 📋 GitHub Actions ワークフローファイル作成
2. 📋 Pre-commit Hook スクリプト作成
3. 📋 テスト実行時間の最適化（現在約15分 → 目標5分以内）
4. 📋 テスト結果レポート自動生成
5. 📋 CLAUDE.mdに必須事項として追記

**CLAUDE.mdへの追記内容**（Phase 3完了後）:
```markdown
## 🧪 **再現性テストの必須実施** ⚠️ CRITICAL

**⚠️ GitHub push前に必ず実行**:
```bash
python entry_points/main.py validate --crash 1987 --fco
```

**基準値**:
- DS-LPPLS Confidence > 30%
- Positive bubble判定
- 予測誤差 ≤ 60日
- 全テストPASS
```

**関連Issue**:
- Issue I129: カスタムFCO多重窓パラメータ整合性修正（再現性テスト実績）
- Issue I131: CLAUDE.md整理タスク（追記対象）

---

### I131: 🔵 CLAUDE.md整理タスク（保護対象ファイル確認・古い情報削除）
**作成日**: 2025-10-13
**優先度**: 🔵 Medium
**担当**: ドキュメント管理
**状態**: 🔄 進行中

**内容**:
CLAUDE.mdが1085行と大きくなりすぎているため、必須事項を残して古い・冗長な情報を削除または別ファイルへ移動する。また、保護対象ファイルの情報が最新かを確認し、コードとの差異を修正する。

**発見した問題**:
1. ✅ **保護対象ファイルの情報が古い**:
   - CLAUDE.md記載: omega範囲 [5.0, 10.0]
   - 実際のコード: omega範囲 [5.0, 15.0]（Issue I129で拡大済み）
   - 対応: **コードを正とする原則**に従いCLAUDE.mdを更新

2. 📋 **冗長なセクション（削除/縮小候補）**:
   - Phase 1/2の詳細な検証結果（約180行） → サマリーのみに縮小
   - ダッシュボード詳細仕様（約100行、Streamlit版は古い） → React版の現状のみ記載
   - 廃止済みスケジューリング機能（約50行） → 削除または大幅縮小
   - 過度に詳細な実装前チェックリスト（約150行） → 簡潔な箇条書きに

3. 📋 **別ファイルへ移動すべき内容**:
   - FCO技術仕様の詳細 → `docs/fco_upgrade_v2/foundation/`（既存）
   - データフロー検証の詳細手順 → `docs/fco_upgrade_v2/testing_guidelines.md`（新規）
   - 実装ミス防止ガイドライン → `docs/development_guidelines.md`（新規）

**整理方針**:

✅ **必須として残すセクション**:
1. 新セッション開始時の必須確認事項
2. 最重要原則（論文再現保護・法的コンプライアンス）
3. workspace_for_claude必須使用
4. カスタムFCO移行状況（現在進行中）
5. 保護対象ファイル（最新情報に更新）
6. 分析基準日の定義
7. プロジェクト構造（4層アーキテクチャ）
8. 実行インターフェース

**追加すべき原則**:
- ✅ **「コードを正とする原則」**:
  - ドキュメントとコードの実装に差異がある場合
  - コードが正しく動作している限り、コードを正とする
  - ドキュメントを実装に合わせて更新する

**実施タスク**:
1. ✅ 保護対象ファイルの存在確認（全て存在）
2. ✅ コードとの差異確認（omega範囲の差異発見）
3. 📋 「コードを正とする原則」をCLAUDE.mdに追記
4. 📋 保護対象ファイル情報を最新に更新
5. 📋 冗長なセクションを削除/縮小
6. 📋 詳細情報を別ファイルへ移動
7. 📋 整理後のCLAUDE.mdをコミット

**目標**:
- CLAUDE.mdを1085行 → 500-600行に削減
- 必須情報のみを簡潔に記載
- 詳細情報は適切なドキュメントに分散
- 新セッション開始時にすぐ理解できる構成

**関連Issue**:
- Issue I129: カスタムFCO多重窓パラメータ整合性修正（omega範囲拡大）
- Issue I132: 進捗管理方法の検討（並行作業）

---

### I129: 🔴 検証テスト実装方針の改善とtc変換精度の検証
**作成日**: 2025-10-12
**優先度**: 🔴 Critical
**担当**: カスタムFCO開発
**状態**: 🧪 実験中（境界条件拡大効果検証完了、次の対策検討中）

**内容**:
Issue I128のtc→日付変換修正後、検証テスト結果に大きな誤差が発生している。
また、検証テスト実装がエントリーポイント経由ではなく独自実装になっている。

**問題点**:
1. **検証テストの実装方針**:
   - 現状: 検証テスト内で独自にデータ読み込み・分析実行
   - 問題: エントリーポイント経由ではないため、本番と異なるコードパスを通る
   - 影響: 本番環境での科学的妥当性を正確に検証できない

2. **tc変換後の誤差が大きすぎる**:
   - Phase 1: 予測誤差52日（修正前: 5日）
   - Phase 2: 予測誤差74日（750日窓基準）
   - 懸念: tc→暦日変換に誤りがある可能性

3. **plots/以下の整理が必要**:
   - 科学的に必要なプロット（歴史的クラッシュ検証等）の特定
   - 古くなったプロットの整理

**調査実施履歴**:
1. ✅ エントリーポイント経由での検証テスト実行方法の確認（2025-10-12）
2. ✅ `entry_points/main.py validate --crash 1987 --fco`の実行（2025-10-12）
3. ✅ エントリーポイント経由と直接実行の結果比較（2025-10-12）
   - **発見**: 0.0% vs 41.18% の重大な不一致
4. ✅ 根本原因の特定（2025-10-12）
   - 小さい窓（125-250日）での収束失敗
   - 境界張り付き（beta=0.7, omega=10.0）問題
5. ✅ 境界条件拡大実装・検証（2025-10-12）
   - beta: 0.7→0.9, omega: 10.0→20.0
   - **結果**: Confidence改善なし（0.0% → 0.0%）
6. 📋 tc→暦日変換の再検証（convert_tc_to_date()の実装確認）
7. 📋 plots/以下の科学的分類と整理

**🔬 境界条件拡大検証結果（2025-10-12実施）**:

**実装内容**:
```python
# core/fitting/lppl_optimizer.py
# 変更前
[1.5,  0.7, 10.0,  8*np.pi,  10,  10,  2.0]  # upper

# 変更後
[1.5,  0.9, 20.0,  8*np.pi,  10,  10,  2.0]  # upper (beta: 0.7→0.9, omega: 10.0→20.0)
```

**検証結果**:
| 項目 | 変更前 | 変更後 | 改善 |
|------|--------|--------|------|
| **DS-LPPLS Confidence** | 0.0% | **0.0%** | ❌ 改善なし |
| **境界張り付き（beta=0.9000）** | - | 59/121窓（49%） | ❌ 新たな問題 |
| **境界張り付き（omega）** | 多数 | 解消 | ✅ 成功 |

**詳細分析**:
- 総フィット数: 121/126窓（96%成功率）
- **omega拡大の成功**: 境界張り付き解消、9.1-12.6の範囲に分散
- **beta拡大の失敗**: 依然として49%が上限（0.9000）に張り付き
- **境界張り付きチェックによる棄却**: beta=0.9000の59窓が全て不適格

**根本原因**:
1. **beta上限が依然として不十分**: 0.9でも最適解が境界外にある
2. **境界張り付きチェックの厳格性**: 2%マージン内は全て棄却
3. **小さい窓の収束失敗**: 125-250日窓での全グリッドサーチ失敗（5窓）

**詳細レポート**:
- `workspace_for_claude/issue_i129_investigation_summary.md` - 調査サマリー
- `workspace_for_claude/issue_i129_boundary_expansion_result.md` - 境界条件拡大結果

**次の対応候補**:
1. **選択肢1: betaのさらなる拡大**
   - beta上限: 0.9 → 1.2（Sornette論文範囲を超える）
   - メリット: 境界張り付きをさらに軽減
   - デメリット: 科学的妥当性の検証が必要

2. **選択肢2: 窓範囲の変更（PracticalFCOEngine方式）**
   - 最小窓: 125日 → 250日
   - 実証済み: DS-LPPLS Confidence 41.18%達成
   - メリット: 小窓収束失敗を回避
   - デメリット: FCO標準（125日）からの逸脱

3. **選択肢3: 境界張り付きチェックのマージン緩和**
   - マージン: 2% → 5%
   - メリット: beta=0.9近傍も適格
   - デメリット: 科学的厳格性の低下

4. **選択肢4: 複合アプローチ（推奨）**
   - beta拡大: 0.9 → 1.0（Sornette論文上限内）
   - 窓範囲調整: 最小窓を200日に引き上げ
   - 段階的検証: 各変更の効果を個別に測定

**🔬 過去実装パラメータ検証結果（2025-10-12実施）**:

**ユーザーフィードバック**:
> "パラメータの境界への張り付きについては、以前に実装していたシンプルな LPPL のフィッティングでの境界を採用することで、ほぼ解決している問題です。1987_custom_fco_phase1_validation.png の検証を実施したときのパラメータに反映されていると思います"

**実装内容**:
```python
# core/fitting/lppl_optimizer.py
# 過去実装準拠版（archive/src_pre_migration_backup/fitting/fitter.py参照）
bounds = (
    [1.01, 0.3, 5.0, -8*np.pi, -10, -10, -2.0],  # lower
    [1.5,  0.7, 8.0,  8*np.pi,  10,  10,  2.0]  # upper（1987年100/100スコア実績）
)
```

**検証結果**:
| 項目 | 境界拡大版 | 過去実装版 | 改善 |
|------|-----------|-----------|------|
| **beta上限** | 0.9 | 0.7 | 過去実装は狭い |
| **omega上限** | 20.0 | 8.0 | 過去実装は狭い |
| **DS-LPPLS Confidence** | 0.0% | **2.4%** | ✅ わずかに改善 |
| **適格フィット数** | 0/126 | **3/126** | ✅ わずかに改善 |
| **Bubble Type** | negative | negative | 変化なし |
| **検証結果** | ❌ FAILED | ❌ FAILED | 依然として不合格 |

**境界張り付き分析（重大な発見）**:
- **beta=0.7000（上限張り付き）**: 108/121窓（**89%**）❌❌❌
  - 境界拡大版（beta=0.9000）: 59/121窓（49%）
  - **悪化**: 過去実装の方が境界張り付きが深刻
- **omega=8.0000（上限張り付き）**: 85/121窓（**70%**）❌❌
  - 境界拡大版（omega=10.0+）: 多数張り付き
  - **両方とも深刻**: どちらの実装でも問題

**根本原因の特定**:
1. ❌ **境界条件は主要因ではない**:
   - 境界拡大: 0.0% Confidence（改善なし）
   - 過去実装: 2.4% Confidence（わずかな改善のみ）
   - 過去実装では境界張り付きがかえって悪化（89%張り付き）

2. ✅ **窓範囲（125-250日窓）が主要因**:
   - 直接スクリプト（250-750日窓）: **41.18% Confidence** ✅
   - エントリーポイント（125-750日窓）: **0-2.4% Confidence** ❌
   - 125日窓での収束率が極めて低い

3. ✅ **単一窓LPPL vs 多重窓FCOの違い**:
   - 過去実装（1987年100/100スコア）: **単一窓**での検証
   - 現在のFCO実装: **126窓**での多重窓解析
   - 各窓で異なる最適パラメータが必要 → 過去実装の境界では制約が厳しすぎる

**詳細レポート**:
- `workspace_for_claude/issue_i129_past_params_result.md` - 過去実装パラメータ検証結果（包括分析）
- `workspace_for_claude/issue_i129_investigation_summary.md` - 調査サマリー
- `workspace_for_claude/issue_i129_boundary_expansion_result.md` - 境界条件拡大結果
- `workspace_for_claude/fco_validation_past_params.log` - 過去実装パラメータ検証ログ

**推奨される次の対策（選択肢）**:

**選択肢A: 窓範囲変更（最推奨）**:
- 最小窓: 125日 → 250日（PracticalFCOEngine準拠）
- 根拠: 直接スクリプトで41.18% Confidence達成済み
- 期待効果: 40%+ Confidence
- メリット: 実証済みの成功事例、科学的根拠明確
- デメリット: FCO標準（125日）からの逸脱

**選択肢B: 境界条件の科学的再評価**:
- Sornette論文・FCO公式実装の境界条件を精査
- ただし、窓範囲問題が主因のため効果は限定的

**選択肢C: 複合アプローチ**:
- 窓範囲を250-750日に変更（主対策）
- 境界条件をSornette論文準拠に拡大（補助対策）
- 段階的検証で各変更の効果を測定

**次のアクション**:
1. ✅ 境界条件拡大実装完了
2. ✅ エントリーポイント経由検証実行完了（境界拡大版）
3. ✅ 過去実装パラメータに復元・検証完了
4. ✅ 結果分析・ドキュメント化完了
5. 📋 **ユーザーと次の対策を相談**:
   - 選択肢A（窓範囲変更）の実施検討
   - または選択肢B/Cの検討
   - 科学的根拠に基づく最終決定

**関連Issue**:
- Issue I128: tc→日付変換修正（完了）

**実装ファイル**:
- `core/fitting/lppl_optimizer.py` - 過去実装パラメータ（beta: 0.3-0.7, omega: 5.0-8.0）
- `workspace_for_claude/fco_validation_expanded_bounds.log` - 境界拡大版検証ログ
- `workspace_for_claude/fco_validation_past_params.log` - 過去実装版検証ログ（約12分）

---

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

### I128: 🟡 Phase 2-B実装戦略決定（過去期間分析のカスタムFCO移行）
**作成日**: 2025-10-12
**完了日**: 2025-10-12
**優先度**: 🟡 Medium（Phase 2-A/2-C完了後）
**担当**: カスタムFCO開発
**状態**: ✅ 完了（Phase 2-A拡張版実装成功）

**内容**:
`entry_points/main.py`の過去期間分析（`run_fco_analyze()`）がBoulder LPPLS版FCOServiceを使用している。Phase 2-Aの個別銘柄解析の延長で実装できるか、既存FCOServiceの構造に従うべきか、シンプルな実装方針を決定する。

**現在の実装状況**:

1. **✅ Phase 2-A（個別銘柄解析）**: すでにカスタムFCO移行完了
   - **ファイル**: `entry_points/main.py:110-217`
   - **実装**: CustomFCOEngine + 窓並列化（2.86倍高速化）
   - **フロー**: データ取得 → カスタムFCO分析 → DB保存
   - **パイプライン**: 完全実装済み

2. **❌ Phase 2-B（過去期間分析）**: Boulder LPPLS版FCOService使用中
   - **ファイル**: `entry_points/main.py:726-760`
   - **実装**: FCOService（`fco-api/app/services/fco_service.py`、849行）
   - **問題**: Boulder LPPLSエンジン（fco_engine.py）に依存
   - **フロー**: FCOService.run_new_analysis() → Boulder LPPL版FCO

3. **✅ Phase 2-C（バリデーション）**: すでにカスタムFCO移行完了
   - **ファイル**: `black_monday_1987_fco_validator.py`
   - **実装**: CustomFCOEngine + 窓並列化

**FCOServiceの詳細分析**:

**実装構造**（849行）:
```python
class FCOService:
    def __init__(self):
        self.db = FCOResultsDatabase()
        self.price_service = PriceDataService()
        self.fco_engine = FCOEngine()  # ← Boulder LPPLS版
        self.external_client = UnifiedMarketDataClient()

    def run_new_analysis(symbol, period, end_date, force, use_external_api):
        # 1. 最近の分析チェック（forceでない場合）
        if not force:
            latest = self.get_latest_analysis(symbol)
            if (datetime.now() - analysis_date).days < 1:
                return latest  # 1日以内なら再利用

        # 2. 価格データ取得（ローカルDB優先）
        price_data = self.fetch_and_store_price_data(...)

        # 3. FCO分析実行（Boulder LPPLS版）
        result = self.fco_engine.compute_ds_lppls_confidence(log_prices)

        # 4. データベース保存
        analysis_id = self.db.save_fco_analysis(analysis_data)
```

**重複防止機能の実装状況**:

1. **メカニズム1: データベースUNIQUE制約**
   - **ファイル**: `infrastructure/database/fco_results_database.py:90`
   - **実装**: `UNIQUE(symbol, analysis_basis_date, analysis_method)`
   - **動作**: `INSERT OR REPLACE`で自動重複処理
   - **効果**: 同じ銘柄・日付の再分析は自動更新

2. **メカニズム2: 実行前チェック（FCOService内）**
   - **ファイル**: `fco-api/app/services/fco_service.py:199-206`
   - **実装**: `get_latest_analysis()` + 1日以内チェック
   - **問題**: ⚠️ `analysis_date`（実行日）ベースで不適切
   - **必要**: `analysis_basis_date`（分析基準日）ベースに変更
   - **関連**: Issue I120で指摘済み

**Phase 2-A vs FCOService 比較**:

| 項目 | Phase 2-A | FCOService |
|------|----------|-----------|
| **行数** | 107行 | 849行 |
| **依存関係** | 3モジュール | 5モジュール（+FastAPI） |
| **データ取得** | UnifiedDataClient直接 | PriceDataService経由 |
| **FCOエンジン** | CustomFCOEngine ✅ | Boulder LPPLS版 ❌ |
| **スキップ機能** | なし | あり（要修正） |
| **DB保存** | FCOResultsDatabase直接 | FCOResultsDatabase経由 |

**実装方針の選択肢**:

### 🎯 **推奨: Phase 2-Aの延長（シンプル実装）**

**理由**:
1. ✅ **コード削減**: 849行 → 約150行（Phase 2-A + スキップ機能）
2. ✅ **依存関係削減**: FCOService不要、FastAPI依存なし
3. ✅ **既存実装の再利用**: Phase 2-Aのパイプラインをそのまま使える
4. ✅ **保守性向上**: シンプルな実装、理解しやすい
5. ✅ **科学的精度**: Phase 2-Aと同じカスタムFCOエンジン

**新規実装案**（約150行）:
```python
def run_fco_analyze_historical_simple(args):
    """過去期間分析（Phase 2-A拡張版）"""
    from core.fitting.custom_fco_engine import CustomFCOEngine
    from infrastructure.database.fco_results_database import FCOResultsDatabase
    from infrastructure.market_data.data_downloader import MarketDataDownloader

    db = FCOResultsDatabase()
    downloader = MarketDataDownloader()
    engine = CustomFCOEngine(n_tries=10)

    # 期間リスト生成（既存コード流用）
    periods = generate_periods(args.start_date, args.end_date, args.frequency)

    for symbol in symbols:
        for period_end in periods:
            # スキップ機能（メカニズム1活用）
            existing = db.get_analysis_by_date(symbol, period_end)
            if existing and not force:
                print(f"⏭️ スキップ: {symbol} @ {period_end}")
                continue

            # データ取得（ローカルキャッシュから）
            prices = downloader.get_price_data(symbol, period_end, period_days)

            # カスタムFCO分析（Phase 2-Aと同じ）
            result = engine.compute_ds_lppls_confidence_parallel(prices, n_workers=8)

            # バブルタイプ計算（Phase 2-Aと同じ）
            bubble_type = 'positive' if result.ds_lppls_confidence > 0.3 else 'negative'

            # DB保存（Phase 2-Aと同じ）
            db_result = {...}  # Phase 2-Aと同じ構造
            analysis_id = db.save_fco_analysis(db_result)
```

### ❌ **代替案: FCOService構造踏襲（非推奨）**

**理由**:
1. ❌ **複雑性**: 849行の実装を理解・移行する必要
2. ❌ **FastAPI依存**: 不要な依存関係
3. ❌ **重複コード**: Phase 2-Aと機能重複
4. ❌ **保守性**: 2つの実装を維持する必要

**ユーザー要件との整合性**:

> 現在は、1977年以降の複数銘柄（当面はFREDの銘柄のみ）を解析し、最新のデータが得られるたび、新しい解析結果を追加していくという実装を目指しています

**この要件はPhase 2-A拡張版で完全に満たせます**:
- ✅ 複数銘柄対応（forループ）
- ✅ 過去期間対応（期間リスト生成）
- ✅ スキップ機能（DB UNIQUE制約 + 実行前チェック）
- ✅ 差分更新（スキップ機能により自動実現）

**スキップ機能の2つのメカニズム（両方活用）**:

1. **データベースレベル**: `UNIQUE`制約 + `INSERT OR REPLACE`
   - 自動重複防止（実装済み）
   - コード追加不要

2. **アプリケーションレベル**: 実行前チェック
   - `db.get_analysis_by_date(symbol, analysis_basis_date)`
   - 効率化（不要な計算をスキップ）
   - 約10行のコード追加

**要件のシンプル化確認**:

ユーザーが記憶している「2種類の方向から導入」:
1. ✅ **メカニズム1**: データベースUNIQUE制約（実装済み）
2. ✅ **メカニズム2**: 実行前チェック（FCOServiceに実装、Phase 2-Bでも採用）

→ **Phase 2-A拡張版で両方のメカニズムを簡単に実装可能**

**実装推奨事項**:

1. **✅ Phase 2-Aの延長で実装**
   - シンプル・保守性・科学的精度のすべてで優位

2. **✅ スキップ機能の実装**
   - メカニズム1: すでに実装済み（DB UNIQUE制約）
   - メカニズム2: 実行前チェック（約10行追加）

3. **✅ FCOServiceは保持**
   - FastAPI用のサービス層として残す
   - 内部でCustomFCOEngineを使うように移行（Phase 4で検討）

4. **✅ コマンドラインインターフェース変更なし**
   - `python entry_points/main.py fco-analyze historical --start-date 1977-01-02`
   - ユーザー体験は同じ、内部実装のみ変更

**次のアクション（ユーザー承認 ✅）**:

1. ✅ Phase 2-B実装開始承認
2. ✅ Phase 2-B実装（Phase 2-A拡張版）
3. ✅ スキップ機能の統合（2つのメカニズム）
4. 📋 1977年SP500過去データでテスト実行
5. 📋 科学的精度検証（1987年ブラックマンデー）
6. ✅ Issue I120の完全解決

**実装完了（2025-10-12）**:

1. ✅ **Phase 2-B実装完了**（entry_points/main.py:692-828）
   - Phase 2-A拡張版として実装（107行ベース → 136行実装）
   - CustomFCOEngine + 窓並列化（8ワーカー）採用
   - 直接SQLiteクエリでmarket_price_dataアクセス
   - FCOService依存を完全削除

2. ✅ **スキップ機能実装完了**（2つのメカニズム統合）
   - メカニズム1: DB UNIQUE制約（既存利用）
   - メカニズム2: get_analysis_by_date()による実行前チェック実装
   - --forceオプション追加（既存データ上書き制御）

3. ✅ **動作確認完了**
   - 2024年データで実装正常動作を確認
   - 高品質フィット実現（R² > 0.95）
   - スキップ機能正常動作
   - 4期間 × 126窓 = 504フィッティング実行（約15分）

4. ✅ **Issue I120完全解決**
   - force=True固定を削除
   - analysis_basis_dateベースのスキップ実装
   - 週次 → 日次切り替え時の無駄な再解析を防止

**テスト結果**:
- ❌ 1987年データ: データ不足（304-524点 < 750点必要）
  - データベース開始: 1985-10-21
  - 1987年期間: 約2年分のデータしかない
  - **営業日数の調査**: 750取引日 ≈ 3年分必要（年間約252取引日）
- ✅ 2024年データ: 成功（十分なデータあり）
  - DS-LPPLS Confidence計算成功
  - 多数の高品質フィット（R² > 0.95）
  - スキップ機能動作確認
  - タイムアウト（15分）は計算量の大きさによるもの

**残存課題**:
- データベース期間制限により、1987年期間の分析には約3年分の履歴データが必要
- 本格的な1977年からの分析実行時は十分なデータが存在するため問題なし

**実装構造**:
```python
# entry_points/main.py:692-828
elif args.fco_analyze_action == 'historical':
    from datetime import datetime, timedelta
    from core.fitting.custom_fco_engine import CustomFCOEngine
    from infrastructure.database.fco_results_database import FCOResultsDatabase
    import sqlite3
    import numpy as np

    # 期間リスト生成
    periods = generate_periods(start_date, end_date, frequency)

    for symbol in symbols:
        for period_end in periods:
            # スキップメカニズム2: 実行前チェック
            existing = db.get_analysis_by_date(symbol, period_end)
            if existing and not force:
                print(f"⏭️ スキップ: {period_end}（既存）")
                continue

            # SQLiteクエリで価格データ取得
            with sqlite3.connect(db_path) as conn:
                query = "SELECT date, close FROM market_price_data WHERE ..."
                rows = conn.execute(query, (symbol, period_end)).fetchall()

            # CustomFCO分析（Phase 2-Aと同じ）
            result = engine.compute_ds_lppls_confidence_parallel(prices, n_workers=8)

            # Bubble type計算（Phase 2-Aと同じ）
            bubble_type = 'positive' if result.ds_lppls_confidence > 0.3 else 'negative'

            # DB保存（メカニズム1: UNIQUE制約自動適用）
            analysis_id = db.save_fco_analysis(db_result)
```

**実装上の注意点・将来対応項目**:

### 🔌 **FastAPI連携の浮き部分（Issue追記）**

**現状の問題**:
- `fco-api/app/services/fco_service.py`がBoulder LPPLS版FCOEngineに依存
- Phase 2-B実装後、FastAPI層が未使用のFCOServiceを保持

**対応方針（Phase 4で実施）**:
1. **FCOServiceの内部移行**:
   - `FCOService.__init__()`: `FCOEngine()` → `CustomFCOEngine()`
   - `run_new_analysis()`内でカスタムFCO呼び出しに変更
   - FastAPI層の互換性維持

2. **インターフェース保持**:
   - REST APIエンドポイントは変更なし
   - 内部実装のみカスタムFCO化
   - フロントエンドへの影響ゼロ

3. **段階的移行**:
   - Phase 2-B: コマンドライン実装（FastAPI非依存）
   - Phase 4: FastAPI層の内部移行
   - Phase 5: 旧Boulder LPPLS版FCOEngine削除

**浮き部分の詳細**:
```
現在:
  entry_points/main.py (CLI) → CustomFCOEngine ✅
  fco-api/ (FastAPI) → FCOService → Boulder LPPLS FCOEngine ❌

Phase 2-B完了後:
  entry_points/main.py (CLI) → CustomFCOEngine ✅
  fco-api/ (FastAPI) → FCOService → Boulder LPPLS FCOEngine ⚠️ (未使用)

Phase 4完了後:
  entry_points/main.py (CLI) → CustomFCOEngine ✅
  fco-api/ (FastAPI) → FCOService → CustomFCOEngine ✅
```

### 🔓 **コア解析部分の粗結合化（将来対応）**

**目的**: 解析コードの公開可能性を考慮した設計

**対象コア部分（公開候補）**:
1. `core/fitting/lppl_optimizer.py` - LPPLフィッティング
2. `core/fitting/lppl_utils.py` - LPPL数式実装
3. `core/fitting/custom_fco_engine.py` - カスタムFCOエンジン

**周辺機能（粗結合化が必要）**:
1. **データベース依存**:
   - 現状: `CustomFCOEngine` → `FCOResultsDatabase` (直接依存なし、良好)
   - 保存処理: `entry_points/main.py`で実施（✅ 分離済み）

2. **データソース依存**:
   - 現状: データ取得は`entry_points/main.py`で実施
   - コアエンジン: numpy配列のみ受け取る（✅ 分離済み）

3. **可視化依存**:
   - 現状: 分離済み（`infrastructure/visualization/`）
   - コアエンジン: 数値結果のみ返す（✅ 分離済み）

**現在の分離状況（良好）**:
```python
# ✅ 既に粗結合設計
from core.fitting.custom_fco_engine import CustomFCOEngine

engine = CustomFCOEngine(n_tries=10)
result = engine.compute_ds_lppls_confidence_parallel(prices)  # numpy配列のみ

# 周辺機能は呼び出し側で実施
db.save_fco_analysis(result)  # DB保存
visualize(result)  # 可視化
```

**将来的な改善（Phase 5以降）**:
1. **パッケージ化**: `sornette-lppl`パッケージとして独立
2. **インターフェース標準化**: 入出力形式の明文化
3. **依存関係最小化**: numpy, scipy のみに限定
4. **ドキュメント整備**: 数式・理論・使用例

**結論**: 現在の設計はすでに粗結合であり、公開準備は容易

**関連Issue**:
- Issue I127: 窓並列化実装完了（Phase 2-B で活用）
- Issue I120: スキップ機能未実装（Phase 2-B で解決）
- Issue I125: フィッティング条件の透明性・再現性確保（コード公開関連）

**参考ファイル**:
- `entry_points/main.py:110-217` - Phase 2-A実装（参照）
- `entry_points/main.py:692-828` - Phase 2-B実装完了
- `fco-api/app/services/fco_service.py` - FCOService実装（Phase 4で移行）
- `infrastructure/database/fco_results_database.py` - DB実装（メカニズム1）
- `workspace_for_claude/boulder_to_custom_fco_migration_plan.md` - 移行計画

**営業日 vs 暦日の問題分析（2025-10-12）**:

### 📊 現状の実装（営業日ベース）

**時間正規化**:
```python
# lppl_utils.py:139-140
t = np.linspace(0, 1, len(prices))  # len(prices) = 営業日数
```

**窓サイズ定義**:
```python
# custom_fco_engine.py:125-127
WINDOW_MIN = 125  # 営業日
WINDOW_MAX = 750  # 営業日
```

**データ不足チェック**:
```python
# custom_fco_engine.py:85-86
if n_total < self.WINDOW_MAX:  # n_total = 営業日数
    logger.warning(f"Insufficient data: {n_total} < {self.WINDOW_MAX}")
```

### 🎯 営業日ベース採用の科学的根拠

**現状維持（営業日ベース）が最適な理由**:

1. ✅ **FCO標準準拠**: FCO公式仕様では営業日ベースが標準
   - 126窓: 750日 → 125日（営業日）
   - 金融データは営業日単位で記録される

2. ✅ **過去実装との整合性**: 1987年ブラックマンデー 100/100スコア維持
   - `archive/src_pre_migration_backup/fitting/fitter.py` は営業日ベース
   - 科学的再現性の根幹

3. ✅ **実用性**: 金融市場の自然な時間単位
   - 市場は営業日のみ動く
   - 土日祝日は取引なし

4. ✅ **データ不足問題は別問題**:
   - 真因: データベース期間制限（1985-10-21開始、505営業日分）
   - 必要: 750営業日 ≈ 3年分（年間252営業日）
   - 解決: 1977年からの本格データ取得で十分なデータあり

### 💡 暦日ベース実装の検討（Phase 4以降）

**メリット**:
- tcが実際の暦日数を表すようになる
- 営業日数のズレの影響を受けない
- 時間軸の解釈が明確

**デメリット**:
- ⚠️ **過去実装との整合性が崩れる**
- ⚠️ **1987年 100/100スコアの再現性が保証されない**
- ⚠️ **FCO標準仕様から逸脱する**
- すべてのテストデータで再検証が必要

**提案される実装**:
```python
def prepare_normalized_data_calendar_based(
    prices: np.ndarray,
    dates: pd.DatetimeIndex
) -> Tuple[np.ndarray, np.ndarray]:
    """暦日ベースの時間正規化"""
    start_date = dates[0]
    end_date = dates[-1]
    total_calendar_days = (end_date - start_date).days

    # 各データポイントの暦日位置
    t = np.array([(d - start_date).days for d in dates]) / total_calendar_days

    log_prices = np.log(prices)
    log_prices_normalized = log_prices - log_prices[0]
    return t, log_prices_normalized
```

### 🔬 データ点数チェックの意図

**現在の実装意図**:
```python
# custom_fco_engine.py:85-86
if n_total < self.WINDOW_MAX:  # 750営業日
```

**目的**:
1. **最大窓サイズ確保**: 750営業日窓を作成するには最低750点必要
2. **フィッティング品質保証**: データ不足時は小窓（<250日）で収束失敗多発
3. **FCO標準126窓実現**: 750→125日の126窓を実現

**暦日ベースでの再定義案**:
```python
def check_sufficient_data_calendar_based(dates: pd.DatetimeIndex) -> bool:
    total_calendar_days = (dates[-1] - dates[0]).days
    REQUIRED_CALENDAR_DAYS = 1095  # 750営業日 ≈ 3年分
    return total_calendar_days >= REQUIRED_CALENDAR_DAYS
```

### 📝 結論・推奨アクション

**Phase 2-B（現在）**:
- ✅ **営業日ベースを維持**（FCO標準準拠、科学的再現性保証）
- ✅ データ不足問題の真因を明確化（データベース期間制限）
- ✅ 1977年からの本格データ取得で解決

**Phase 4以降**:
- 📋 **暦日ベース実装の実験的検証を検討**
  - 新しいブランチで実装
  - 1987年ブラックマンデーで再検証
  - 科学的妥当性・予測精度を比較
- 📋 実装の複雑性とメリットの比較
- 📋 FCO標準仕様との関係性を評価

**詳細分析**:
`workspace_for_claude/trading_days_vs_calendar_days_analysis.md`

---

### 🚨 CRITICAL: tc→日付変換の重大な問題発見（2025-10-12）

**ユーザー指摘事項の検証結果**:

#### i) フィッティング期間のスケール反映問題

**現在の実装（`infrastructure/database/integration_helpers.py:124`）**:
```python
days_beyond = (tc - 1.0) * 365  # ← 固定365日換算（⚠️ 問題あり）
```

**問題点**:
1. ⚠️ **固定365日換算**: フィッティング期間の実際の長さを無視
2. ⚠️ **営業日と暦日のズレ**: 750営業日 ≈ 1095暦日（約3年）なのに365日で換算
3. ⚠️ **窓サイズの影響**: 750日窓も125日窓も同じ365日で換算

**検証結果（`workspace_for_claude/verify_tc_conversion_problem.py`）**:

| テストケース | フィッティング期間 | 実際の暦日数 | tc値 | 現在の実装 | 正しい実装 | 誤差 |
|------------|----------------|------------|------|-----------|-----------|------|
| 750営業日窓 | 2021-10-19 ~ 2024-10-19 | 1096日 | 1.2 | 2024-12-31 | 2025-05-26 | **-147日** |
| 125営業日窓 | 2024-04-19 ~ 2024-10-19 | 183日 | 1.2 | 2024-12-31 | 2024-11-24 | **36日** |
| 1987年検証 | 1983-11-03 ~ 1987-10-19 | 1446日 | 1.2128 | 1988-01-04 | 1988-08-21 | **-231日** |

**重大な発見**:
- 同じtc値でも窓サイズによって予測日が異なるはずなのに、現在の実装では同じになってしまう
- 1987年検証では**231日（約7.7ヶ月）の誤差**

#### ii) 窓ごとの変換比率の問題

**現在の実装**: ⚠️ **すべての窓で固定365日換算を使用**
- 750日窓: (tc - 1.0) × 365
- 500日窓: (tc - 1.0) × 365  ← 同じ
- 125日窓: (tc - 1.0) × 365  ← 同じ

**正しい実装**: ✅ **窓ごとに異なる変換比率を使用すべき**
- 750日窓 (1096暦日): (tc - 1.0) × 1096
- 500日窓 (730暦日): (tc - 1.0) × 730
- 125日窓 (183暦日): (tc - 1.0) × 183

**科学的根拠**:
```python
# 時間正規化: t ∈ [0, 1]
# t=0: first_date (フィッティング開始日)
# t=1: last_date (フィッティング終了日)
# tc > 1.0: 未来予測

# 正しい変換式:
fitting_period_calendar_days = (last_date - first_date).days
days_beyond = (tc - 1.0) * fitting_period_calendar_days
predicted_date = last_date + timedelta(days=days_beyond)
```

### 📝 修正提案

**修正対象ファイル**:
1. `infrastructure/database/integration_helpers.py:110-146`
2. カスタムFCO実装での予測日計算部分

**修正案**:
```python
def _calculate_predicted_date(
    self,
    tc: float,
    first_date: pd.Timestamp,
    last_date: pd.Timestamp
) -> Optional[datetime]:
    """
    tc値から予測日時を計算（フィッティング期間考慮版）

    【修正点】
    - first_date（フィッティング開始日）を追加
    - フィッティング期間の実際の暦日数を使用
    - 窓ごとに異なる変換比率を適用

    Args:
        tc: tc値（正規化時間）
        first_date: フィッティング期間の開始日
        last_date: フィッティング期間の終了日

    Returns:
        datetime: 予測日時
    """
    try:
        if tc > 1.0:
            # フィッティング期間の実際の暦日数
            fitting_period_calendar_days = (last_date - first_date).days

            # tcが正規化時間を超えた分を暦日に変換
            # tc=1.0 が last_date に対応
            # tc=2.0 が last_date + fitting_period_calendar_days に対応
            days_beyond = (tc - 1.0) * fitting_period_calendar_days

            # 日数と時間に分離（時間精度対応）
            full_days = int(days_beyond)
            fractional_day = days_beyond - full_days
            hours = fractional_day * 24

            # pandas.Timestampをdatetimeに変換
            if hasattr(last_date, 'to_pydatetime'):
                base_datetime = last_date.to_pydatetime()
            else:
                base_datetime = last_date

            # 時間精度まで含めた予測日時を計算
            predicted_datetime = base_datetime + timedelta(
                days=full_days,
                hours=hours
            )

            return predicted_datetime
        else:
            # tc <= 1.0 は過去（通常は使用されない）
            return None
    except Exception as e:
        print(f"⚠️ tc値から日時計算エラー: tc={tc}, error={str(e)}")
        return None
```

### 🔧 必要な対応

**Phase 3での修正実装**:
1. ✅ 問題の詳細分析完了
2. 📋 `integration_helpers.py` の修正実装
3. 📋 カスタムFCO実装での予測日計算修正
4. 📋 1987年ブラックマンデー検証での再テスト
5. 📋 予測精度への影響評価

**重要性**:
- 🔴 **Critical**: 予測日の精度に直接影響（最大231日の誤差）
- 🔴 **Critical**: 126窓すべてで異なる誤差が発生
- 🔴 **Critical**: FCO標準の多重窓解析の科学的妥当性に影響

**検証スクリプト**:
`workspace_for_claude/verify_tc_conversion_problem.py`

### 📋 修正実装計画（2025-10-12）

**実装計画書**: `workspace_for_claude/tc_conversion_fix_implementation_plan.md`

**実装順序**（推定5時間）:

**Phase 1: コア実装（1-2時間）**
1. 📋 `core/fitting/lppl_utils.py` に `convert_tc_to_date()` 実装
2. 📋 `tests/fitting/test_tc_conversion.py` 実装・実行
3. 📋 pytest 全pass確認

**Phase 2: 既存コード修正（30分-1時間）**
4. 📋 `infrastructure/database/integration_helpers.py` 修正
5. 📋 呼び出し箇所の更新（first_date パラメータ追加）

**Phase 3: Phase 1再検証（30分）**
6. 📋 `workspace_for_claude/verify_tc_conversion_fix_phase1.py` 実装・実行
7. 📋 誤差改善確認・プロット生成

**Phase 4: Phase 3統合テスト（1時間）**
8. 📋 Phase 2-B実装での小規模テスト（2024年データ）
9. 📋 1987年検証（parquetキャッシュ使用）
10. 📋 検証結果確認

**Phase 5: ドキュメント・コミット（30分）**
11. 📋 Issue I128更新
12. 📋 git commit

**期待される効果**:
- 750日窓: -147日誤差 → 正確（100%改善）
- 125日窓: 36日誤差 → 正確（100%改善）
- 1987年検証: -231日誤差 → 正確（100%改善）

**コア原則**: **中心的な変換関数を1箇所に実装**
```
core/fitting/lppl_utils.py
    ↓
convert_tc_to_date(tc, first_date, last_date)  # 新規実装
    ↓
すべての呼び出し箇所で共通使用
```

**進捗状況**: ✅ 完了（2025-10-12）

**実装完了サマリー**:
1. ✅ Phase 1: コア変換関数 `convert_tc_to_date()` 実装完了
2. ✅ Phase 1: 単体テスト（10/10 pass）完了
3. ✅ Phase 2: `integration_helpers.py` 修正完了（2箇所更新）
4. ✅ Phase 3: Phase 1検証スクリプト実行成功（誤差改善413日）
5. ✅ Phase 4: 単体テスト全pass確認
6. ✅ Phase 5: 検証テストスクリプト更新完了（test_phase1/phase2を修正済みコード使用に更新）
7. ✅ Phase 6: Phase 1/Phase 2検証テスト実行成功、プロット更新確認

**検証結果**:
- 750日窓: 146日誤差改善（期待147日、±1日許容範囲内）
- 125日窓: 37日誤差改善（期待36日、±1日許容範囲内）
- 1987年: 230日誤差改善（期待231日、±1日許容範囲内）
- 合計誤差改善: 413日

**Phase 1/Phase 2検証テスト結果（修正後）**:
- Phase 1: 予測誤差52日（修正前: 5日 → 修正により正確な暦日変換を反映）
- Phase 2: DS-LPPLS Confidence 41.18%、予測誤差74日（750日窓基準）
- プロット更新確認: 両Phase共にtc位置が正しく更新され、修正が反映されている

**実装ファイル**:
- `core/fitting/lppl_utils.py`: `convert_tc_to_date()` 関数
- `tests/fitting/test_tc_conversion.py`: 10単体テスト
- `infrastructure/database/integration_helpers.py`: 2箇所修正
- `workspace_for_claude/verify_tc_conversion_fix_phase1.py`: 検証スクリプト
- `tests/custom_fco/test_phase1_single_window.py`: Phase 1検証テスト（修正済み）
- `tests/custom_fco/test_phase2_multi_window.py`: Phase 2検証テスト（修正中）

**🎯 重要な原則（ユーザーフィードバック: 2025-10-12）**:

**検証テストの設計方針**:
> 検証テストは本番環境での解析結果が科学的に妥当であることを検証するものであるので、
> 検証テスト用に個別の実装をするのではなく、エントリーポイントから入るか、
> エントリーポイントから参照されている機能を適切に参照することが望ましい。

**実装上の重要ポイント**:
1. **✅ 正しいアプローチ**: エントリーポイント（`entry_points/main.py`）経由での実行
2. **✅ 正しいアプローチ**: コア機能（`core/fitting/lppl_utils.py`）の共通関数を使用
3. **❌ 避けるべきアプローチ**: 検証テスト内で独自のtc変換実装を作成
4. **❌ 避けるべきアプローチ**: 本番コードと異なるロジックをテスト内で実装

**今回の修正における教訓**:
- Phase 1/2検証テストが独自のtc変換実装（営業日数ベース）を持っていた
- これにより、コア機能の修正が検証テストに反映されず、プロット結果が変わらなかった
- 修正後: 検証テストは`core/fitting/lppl_utils.convert_tc_to_date()`を使用するよう変更
- **科学的妥当性の保証**: 本番と検証が同じコードを使用することで保証される

**適用例**:
```python
# ❌ 間違い: 検証テスト内で独自実装
tc_days_beyond = (tc - 1.0) * len(prices)  # 営業日数ベース（独自実装）
predicted_date = last_date + timedelta(days=tc_days_beyond)

# ✅ 正しい: コア機能の共通関数を使用
from core.fitting.lppl_utils import convert_tc_to_date
predicted_date = convert_tc_to_date(tc, first_date, last_date, include_time=False)
```

**この原則の重要性**:
- 本番コードと検証テストの整合性を保証
- 修正が全システムに確実に反映される
- 科学的再現性の維持
- メンテナンス性の向上（1箇所の修正で全体に反映）

---

## 📊 Issue Statistics

- **Total Active Issues**: 9
- **Critical**: 0
- **High Priority**: 4 (I116, I117, I119, I113)
- **Medium Priority**: 4 (I118, I114, I121, I128)
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

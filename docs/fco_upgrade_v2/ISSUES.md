# FCO v2.1 Issue Tracking

**プロジェクト**: FCO v2.1 React + FastAPI Dashboard
**開始日**: 2025-09-14
**最終更新**: 2025-10-09

---

## 📋 Active Issues

### Issue #001: User Defined モードでの期間変更時エラー

**優先度**: 🔴 High
**ステータス**: Open
**報告日**: 2025-10-09
**カテゴリ**: Frontend / UI Bug

**問題の説明**:
User Defined モードで期間（日数）の入力を変更するとエラーが発生する。

**再現手順**:
1. FCO Dashboard (localhost:3001) にアクセス
2. Analysis Period Filter で "User Defined" を選択
3. "Period (days)" の入力フィールドで値を変更
4. エラーが発生（詳細は要確認）

**影響範囲**:
- User Defined モードが使用不可
- ユーザーが任意の期間を指定できない

**原因の可能性**:
- State管理の不整合
- Date範囲計算のエラー
- API呼び出しのパラメータ不正

**関連ファイル**:
- `fco-dashboard-frontend/pages/index.tsx` (Line 50-80付近)
- `fco-dashboard-frontend/components/charts/FCOScatterPlot.tsx`

**修正方針**:
1. エラーの詳細ログを確認
2. `periodDays` state更新時の処理を検証
3. `baseDate` と `periodDays` の整合性チェック

**関連Issue**: #002

---

### Issue #002: 期間選択UIの改善 - 段階的選択の実装

**優先度**: 🟡 Medium
**ステータス**: Open
**報告日**: 2025-10-09
**カテゴリ**: Frontend / UI Enhancement

**問題の説明**:
現在の期間選択が1日刻みで実用的でない。Gmail の再接続アルゴリズムのような段階的（exponential steps）な選択肢を提供すべき。

**現在の仕様**:
- `periodDays` を1日〜無制限で入力可能
- 1日刻みのステップ
- 実用性が低い

**提案される改善**:

#### 段階的期間選択（10段階）

| ステップ | 期間 | データポイント | 推定ロード時間 |
|---------|------|---------------|---------------|
| 1 | 1ヶ月 | ~4件 | ~50ms |
| 2 | 3ヶ月 | ~13件 | ~60ms |
| 3 | 6ヶ月 | ~26件 | ~80ms |
| 4 | 1年 | ~52件 | ~100ms |
| 5 | 2年 | ~104件 | ~150ms |
| 6 | 3年 | ~156件 | ~200ms |
| 7 | 5年 | ~260件 | ~300ms |
| 8 | 10年 | ~520件 | ~400ms |
| 9 | 20年 | ~1,040件 | ~600ms |
| 10 | 全期間 (48年) | ~2,496件 | ~700ms |

#### 実装案

**Option 1: ドロップダウン選択（推奨）**
```tsx
<select value={periodDays} onChange={(e) => setPeriodDays(parseInt(e.value))}>
  <option value={30}>1ヶ月</option>
  <option value={90}>3ヶ月</option>
  <option value={180}>6ヶ月</option>
  <option value={365}>1年</option>
  <option value={730}>2年</option>
  <option value={1095}>3年</option>
  <option value={1825}>5年</option>
  <option value={3650}>10年</option>
  <option value={7300}>20年</option>
  <option value={-1}>全期間</option>
</select>
```

**Option 2: ボタン選択**
```tsx
<div className="flex gap-2">
  {PERIOD_OPTIONS.map(opt => (
    <button onClick={() => setPeriodDays(opt.days)}>
      {opt.label}
    </button>
  ))}
</div>
```

**Option 3: User Defined モードの簡素化**
- Latest/Historical モードのみ提供
- User Defined を削除または大幅簡素化

#### データサイズ分析結果

**全期間（48年）のデータ量**:
- FCO分析結果: ~175 KB (gzip圧縮後)
- 時系列データ: ~145 KB (gzip圧縮後)
- **合計**: ~320 KB

**ロード時間（標準ブロードバンド 25 Mbps）**:
- ネットワーク: ~100ms
- レンダリング: ~600ms
- **合計**: ~700ms

**結論**: 全期間でも十分高速。API間引き機能は現時点で不要。

#### 関連ドキュメント
- `workspace_for_claude/data_size_analysis.md` - データサイズ・通信速度試算

**修正方針**:
1. User Defined モードをドロップダウン選択に変更
2. 10段階の期間オプションを提供
3. Latest/Historical モードはそのまま維持

**実装優先度**: Medium（Issue #001 修正後に実装）

**関連Issue**: #001

---

## 🔧 Resolved Issues

*(現在なし)*

---

## 📊 Issue Statistics

- **Total Issues**: 2
- **Open**: 2
- **In Progress**: 0
- **Resolved**: 0
- **Priority Distribution**:
  - High: 1
  - Medium: 1
  - Low: 0

---

**管理者**: Claude Code
**最終更新**: 2025-10-09 20:45

# FCO v2.1 Implementation Plan - Next Steps

**作成日**: 2025-01-15
**更新日**: 2025-01-15
**対象**: FCO v2.1 React+FastAPI実装

## 🎯 実装優先順位

### Phase 1: 時系列チャート実装（今週）

#### 1.1 LPPL時系列チャート
```typescript
// components/charts/FCOTimeSeriesChart.tsx
- Plotly.jsを使用（既存の散布図と統一）
- 実際の価格データ + LPPLフィッティング曲線
- 予測クラッシュ日の垂直線表示
- DS-LPPLS Confidence/Trustの表示
```

#### 1.2 表示モード別実装
```typescript
// Scatter Plot Mode
- Top by Confidence (上位N個、デフォルトN=3)
- Recent Analysis (最新N個、デフォルトN=3)
- Selected Point (クリック選択、N=1固定)

// Clustering Mode
- Top by Confidence per Cluster (各クラスターN個、デフォルトN=1)
- Nearest to Cluster Mean (平均最近傍N個、デフォルトN=1)
- Recent Analysis per Cluster (各クラスター最新N個、デフォルトN=1)
```

#### 1.3 UI要素
```typescript
// components/ui/TopNSelector.tsx
- N値選択用セレクトボックス
- モード別の最大値制限
- リアルタイム更新対応
```

### Phase 2: リアルタイム機能（来週）

#### 2.1 WebSocket統合
```python
# fco-api/app/api/websocket/realtime.py
- FastAPI WebSocketエンドポイント
- リアルタイム分析結果配信
- 接続管理とエラーハンドリング
```

#### 2.2 フロントエンド統合
```typescript
// hooks/useWebSocket.ts
- WebSocket接続管理
- 自動再接続機能
- メッセージハンドリング
```

### Phase 3: 認証システム（2週間後）

#### 3.1 バックエンド認証
```python
# fco-api/app/core/security.py
- JWT Bearer Token実装
- ユーザー認証・認可
- APIエンドポイント保護
```

#### 3.2 フロントエンド認証
```typescript
// contexts/AuthContext.tsx
- 認証状態管理
- ログイン/ログアウト機能
- 保護ルートの実装
```

## 📝 実装詳細

### 時系列チャート実装計画

#### Phase 1-A: 基本実装（Scatter Mode + Top Confidence）
```typescript
// 1. 単一時系列チャートコンポーネント
components/charts/FCOTimeSeriesChart.tsx
- 価格データ表示（実線）
- LPPLフィット曲線（破線）
- 予測クラッシュ日（垂直線）
- Plotly.jsで実装（既存と統一）

// 2. Scatter Mode用コンテナ
components/charts/ScatterTimeSeries.tsx
- Top 3 by Confidenceの固定表示
- グリッドレイアウト（1〜3列）
- 各チャートにタイトル・メタデータ表示
```

#### Phase 1-B: N値選択機能
```typescript
// 1. セレクターコンポーネント
components/ui/TopNSelector.tsx
- ドロップダウンまたはスライダー
- モード別の制約（max値）
- onChange時の即座反映

// 2. State管理
pages/index.tsx
- const [topN, setTopN] = useState(3)
- useEffectでモード変更時のリセット
```

#### Phase 1-C: Recent Analysis追加
```typescript
// 表示モード拡張
- ラジオボタンでモード切替
- analysis_basis_dateでソート
- 同じTopNSelectorを使用
```

#### Phase 2-A: Click Selection機能
```typescript
// 1. Plotlyクリックイベント
FCOScatterPlot.tsx
- onClickハンドラー追加
- 選択点のハイライト表示
- customdataで詳細情報渡し

// 2. Selected Point表示
- モード自動切替
- 単一チャート表示（N=1固定）
- クリアボタン追加
```

#### Phase 2-B: Clustering Mode基本実装
```typescript
// 1. クラスター用コンテナ
components/charts/ClusterTimeSeries.tsx
- クラスターごとの境界明確化
- 各クラスターのメタデータ表示
- グリッドレイアウト（クラスター数依存）

// 2. クラスター平均線
- 各チャートに垂直破線追加
- アノテーションで"Cluster Mean"表示
```

#### Phase 2-C: Clustering全モード実装
```typescript
// 追加モード
- Nearest to Mean（平均最近傍）
- Recent per Cluster（各クラスター最新）
- 各モードでN値選択可能
```

## 🔧 技術的考慮事項

### パフォーマンス最適化
- React.memoによるコンポーネントメモ化
- useMemoによる計算結果キャッシュ
- 仮想スクロールによる大量データ対応

### エラーハンドリング
- Error Boundaryの実装
- API呼び出しのリトライロジック
- ユーザーフレンドリーなエラーメッセージ

### テスト戦略
- Jest + React Testing Libraryによるユニットテスト
- Cypressによるe2eテスト
- Storybookによるコンポーネントカタログ

## 📅 実装タイムライン

### 時系列チャート実装スケジュール

| Phase | タスク | 期間 | 成果物 |
|-------|--------|------|--------|
| 1-A | 基本時系列チャート | 1日 | FCOTimeSeriesChart.tsx |
| 1-B | N値選択機能 | 0.5日 | TopNSelector.tsx |
| 1-C | Recent Analysis | 0.5日 | モード切替UI |
| 2-A | Click Selection | 1日 | インタラクティブ選択 |
| 2-B | Clustering基本 | 1日 | ClusterTimeSeries.tsx |
| 2-C | Clustering全モード | 1日 | 完全な機能実装 |

## ✅ 完了条件

### Phase 1完了条件
- [ ] FCOTimeSeriesChart.tsx実装
- [ ] Scatter Mode + Top Confidence表示確認
- [ ] N値選択機能動作確認
- [ ] Recent Analysisモード追加
- [ ] グリッドレイアウト確認

### Phase 2完了条件
- [ ] Click Selection機能実装
- [ ] 選択点ハイライト表示
- [ ] Clustering Mode基本実装
- [ ] クラスター平均線表示
- [ ] 全モード動作確認

## 🎯 実装チェックポイント

### 各Phaseでユーザー確認を実施
1. **Phase 1-A後**: 基本チャート表示の確認
   - LPPLフィット曲線の見た目
   - 予測日の表示方法
   - チャートサイズ・配置

2. **Phase 1-B後**: N値選択UIの確認
   - セレクターのデザイン
   - 値の範囲（最大値）
   - 更新時の挙動

3. **Phase 2-A後**: クリック機能の確認
   - 選択時のフィードバック
   - Selected表示への切替
   - クリア機能の必要性

## 🚀 次のアクション

1. **まず確認事項**
   - APIエンドポイントの確認（時系列データ取得）
   - LPPLフィッティングデータの形式確認
   - 必要なデータがAPIから取得可能か

2. **Phase 1-A開始**
   - FCOTimeSeriesChart.tsxの基本実装
   - モックデータでの表示テスト
   - Plotly.jsでの実装開始

---

**注意事項**:
- 各フェーズは並行して進めることも可能
- ユーザーフィードバックを随時反映
- パフォーマンス監視を継続的に実施
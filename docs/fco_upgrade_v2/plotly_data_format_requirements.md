# Plotly データフォーマット要件（重要）

## 🚨 **最重要事項: Plotlyでのデータ表示における必須要件**

### 問題の発見と解決（2025年1月）

FCOダッシュボード実装中に、Plotlyでデータが表示されない重大な問題を発見し、解決しました。

### ✅ **正しい実装方法**

```python
# Plotlyでプロットする際は、必ず.valuesでnumpy配列形式にする
x_dates = valid_data['analysis_basis_date'].values  # ← 必須: .values
y_dates = valid_data['predicted_crash_date'].values  # ← 必須: .values
confidence_values = (valid_data['ds_lppls_confidence'] * 100).values  # ← 必須: .values

fig.add_trace(go.Scatter(
    x=x_dates,  # numpy array形式
    y=y_dates,  # numpy array形式
    mode='markers',
    marker=dict(
        size=12,
        color=confidence_values,  # numpy array形式
        colorscale='Viridis',  # LPPLと同じカラースケール
        showscale=True
    )
))
```

### ❌ **避けるべき実装パターン**

```python
# ❌ 間違い: pandas Series/DataFrameを直接渡す
fig.add_trace(go.Scatter(
    x=valid_data['analysis_basis_date'],  # pandas Series
    y=valid_data['predicted_crash_date'],  # pandas Series
))

# ❌ 間違い: tolist()を使用
fig.add_trace(go.Scatter(
    x=valid_data['analysis_basis_date'].tolist(),
    y=valid_data['predicted_crash_date'].tolist(),
))

# ❌ 間違い: 日付型の直接渡し（場合によっては動作しない）
fig.add_trace(go.Scatter(
    x=pd.to_datetime(valid_data['analysis_basis_date']),
    y=pd.to_datetime(valid_data['predicted_crash_date']),
))
```

### 📋 **チェックリスト**

プロット実装時の必須確認事項：

1. ☑️ データは`.values`でnumpy配列に変換されているか
2. ☑️ X軸、Y軸、カラー値すべてがnumpy配列形式か
3. ☑️ データ型の確認（特に日付型）
4. ☑️ 空データのチェック（`if not data.empty:`）

### 🔍 **デバッグ方法**

プロットが表示されない場合の確認手順：

```python
# 1. データの存在確認
print(f"データ件数: {len(valid_data)}")
print(f"empty?: {valid_data.empty}")

# 2. データ型の確認
print(f"x_dates type: {type(x_dates)}")
print(f"x_dates shape: {x_dates.shape}")
print(f"First value: {x_dates[0] if len(x_dates) > 0 else 'empty'}")

# 3. Figureの確認
print(f"Traces in figure: {len(fig.data)}")
```

### 🏗️ **アーキテクチャー上の重要性**

この要件は、FCOダッシュボードだけでなく、すべてのPlotlyベースの可視化において適用される必須要件です。

- **FCOダッシュボード**: `infrastructure/visualization/fco_dashboard_components.py`
- **LPPLダッシュボード**: `applications/dashboards/main_dashboard.py`
- **テストスクリプト**: `workspace_for_claude/test_*.py`

### 📚 **参考情報**

- 発見日: 2025年1月14日
- 問題: pandas DataFrame/Seriesを直接Plotlyに渡してもプロットが表示されない
- 解決策: `.values`でnumpy配列形式に変換
- 検証済み: `test_fco_real_data.py`で動作確認済み
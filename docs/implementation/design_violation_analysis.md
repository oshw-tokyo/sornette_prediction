# API設計違反の原因分析レポート

## 🚨 問題の概要

ユーザーの指摘通り、実装が**本来の設計から大きく逸脱**している。
カタログによる排他的API割り当て設計が、フォールバック機能により破綻している。

## 📋 本来の設計仕様（ユーザー要件）

> FRED で取り扱いのある銘柄はFREDで取得し、（それ以外で）仮想通貨の銘柄は CoinGecko で取得し、それ以外で代表的な銘柄で選定済みのものを Alpha Vantage(?)で取得してという使い分けを、事前のスケジュール（カタログ）で割当済みにしていた想定

### 期待される動作
- **排他的割り当て**: 各銘柄は1つのAPIのみを使用
- **事前決定**: カタログでprimaryプロバイダーを指定
- **フォールバック禁止**: 失敗時は他のAPIを試さない

## ❌ 現在の実装問題

### 1. `unified_data_client.py` の設計違反箇所

#### A. fallback読み込み（Lines 114-120）
```python
# fallback sourcesも処理  ← これが違反
fallbacks = sources.get('fallbacks', [])
for fallback in fallbacks:
    if isinstance(fallback, dict) and 'provider' in fallback:
        provider = fallback['provider']
        provider_symbol = fallback.get('symbol', symbol)
        symbol_mapping[provider] = provider_symbol
```

#### B. 全API試行ロジック（Lines 174-177）
```python
# 残りのソースを追加  ← これが最大の違反
for source in self.available_sources:
    if source not in sources_to_try:
        sources_to_try.append(source)
```

#### C. メソッド名が示す設計意図の違反（Line 133）
```python
def get_data_with_fallback(self, symbol: str, ...):  # ← fallbackが前提の設計
```

### 2. 実際の動作例（BNBの場合）

**本来の設計での期待動作**:
```
BNB → CoinGeckoのみでbinancecoinとして取得
失敗した場合 → エラーとして処理、他APIは試行しない
```

**現在の実装での実際動作**:
```
BNB → CoinGecko試行 → 失敗 → FRED試行 → Alpha Vantage試行 → 全API試行
```

## 📊 カタログ分析結果（正常）

カタログ自体は正しく設計されている：
- **FRED**: 24銘柄（インデックス、為替、一部仮想通貨）
- **CoinGecko**: 34銘柄（仮想通貨専用）
- **Alpha Vantage**: 20銘柄（ETF、債券等）

## 🔧 必要な修正

### 1. メソッド名変更
```python
get_data_with_fallback() → get_data_exclusive()
```

### 2. 排他的取得ロジック実装
```python
def get_data_exclusive(self, symbol: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    # primaryプロバイダーのみ使用
    # fallbackロジック完全削除
    # 失敗時は即座にNone返却
```

### 3. カタログfallback情報の無視
現在はfallback情報を読み込んでいるが、これを無視する。

### 4. エラーハンドリングの変更
他APIでの再試行ではなく、明確な失敗として扱う。

## 📈 修正による効果

1. **API呼び出し効率化**: 不要な試行が削減される
2. **設計整合性**: カタログ設計と実装の一致
3. **予測可能性**: どのAPIが使用されるか事前に確定
4. **デバッグ容易性**: エラー原因の特定が簡単

## ⚠️ 修正時の注意点

1. **後方互換性**: 既存のcaller側での調整が必要
2. **エラーメッセージ**: よりわかりやすいエラー情報の提供
3. **テスト**: 修正後の論文再現テスト（100/100スコア維持）

---

**結論**: 実装がカタログベースの排他的API設計を完全に無視し、フォールバック機能により全API試行する設計に変質している。これは明確な設計違反であり、即座の修正が必要。
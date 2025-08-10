# Deprecated API Implementation Backup

**バックアップ作成日**: 2025-08-10  
**理由**: CoinGecko/Alpha Vantage API制限・不安定性による代替API実装準備

## バックアップファイル

### 1. CoinGecko Client
- **ファイル**: `coingecko_client.py`
- **実装状況**: 部分的動作 (15/37銘柄取得)
- **主要問題**: APIキー未設定、レート制限、主要仮想通貨未取得

### 2. Unified Data Client
- **ファイル**: `unified_data_client.py`
- **実装状況**: FRED正常、CoinGecko/Alpha Vantage問題あり
- **統合機能**: 3層APIフォールバック戦略

### 3. Market Data Catalog  
- **ファイル**: `market_data_catalog.json`
- **銘柄数**: 79銘柄（FRED: 42, CoinGecko: 37）
- **カバレッジ**: CoinGecko 40.5%、総合49.4%

## 問題分析

### Critical Issues
- **I048**: analysis_basis_date NULL (95.8%のデータ)
- **I049**: CoinGecko低カバレッジ (BTC,ETH,USDT,USDC未取得)

### API制限状況
- **CoinGecko**: 10req/分 (無料)
- **Alpha Vantage**: 25-500req/日
- **FRED**: 正常動作

## 代替API戦略

### 優先候補
1. **Twelve Data** (800req/日)
2. **BlockMarkets** (無制限)  
3. **Binance API** (1200req/分)
4. **Coinbase API** (10000req/時)

## 復旧方法

万一、代替API実装で問題が発生した場合の復旧手順：

```bash
# 1. バックアップからの復旧
cp backup/deprecated_apis/coingecko_client.py infrastructure/data_sources/
cp backup/deprecated_apis/unified_data_client.py infrastructure/data_sources/
cp backup/deprecated_apis/market_data_catalog.json infrastructure/data_sources/

# 2. 論文再現テスト実行
python entry_points/main.py validate --crash 1987

# 3. システム動作確認
python entry_points/main.py analyze NASDAQCOM
```

## 注意事項

- 論文再現システム（1987年ブラックマンデー: 100/100スコア）の絶対保護
- 段階的な代替API実装推奨
- 各変更後の動作確認必須

---
*バックアップ作成者: Claude Code*
*関連Issue: I048, I049*
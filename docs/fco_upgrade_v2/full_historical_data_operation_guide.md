# 全履歴データアーキテクチャ運用ガイド

## 📚 概要

本ガイドは、FCO v2.0で実装された**全履歴データアーキテクチャ**の運用方法を説明します。このアーキテクチャにより、1987年ブラックマンデー、2000年ドットコムバブル、2008年金融危機など、歴史的クラッシュを含む全期間のFCO分析が可能になります。

## 🏗️ アーキテクチャ構成

### データストレージ構造
```
data/market_data/
├── daily/                    # 日次データ（階層的保存）
│   └── {symbol}/
│       └── {year}/
│           └── {month}.parquet
├── cache/
│   ├── prepared/             # 2年キャッシュ（互換性維持）
│   │   └── {symbol}_2y.parquet
│   └── full/                 # 全履歴キャッシュ（新規）
│       └── {symbol}_full.parquet
└── metadata/
    └── data_catalog.json     # メタデータ
```

### 主要コンポーネント

1. **MarketDataDownloader** (`infrastructure/market_data/data_downloader.py`)
   - 全履歴データの取得と保存
   - 増分更新（差分ダウンロード）
   - 2年/全履歴の両方をサポート

2. **FCODailyAnalyzer** (`applications/analysis_tools/fco_daily_analyzer.py`)
   - 全履歴データを使用したFCO分析
   - 任意の過去日付での分析実行
   - 自動的に適切なキャッシュを選択

## 🚀 基本的な使用方法

### 1. 全履歴データのダウンロード

```python
from infrastructure.market_data.data_downloader import MarketDataDownloader

# 全履歴モードでダウンローダー初期化
downloader = MarketDataDownloader(use_full_history=True)

# 個別銘柄の全履歴をダウンロード
downloader.download_symbol_data('SP500', download_full=True)

# 複数銘柄を一括ダウンロード
symbols = ['SP500', 'NASDAQCOM', 'DJI', 'BTC']
downloader.download_all_symbols(symbols=symbols, download_full=True)
```

### 2. 過去のクラッシュ日でのFCO分析

```python
from applications.analysis_tools.fco_daily_analyzer import FCODailyAnalyzer

# 全履歴モードで分析器初期化
analyzer = FCODailyAnalyzer(use_full_history=True)

# 1987年ブラックマンデー直前の分析
analyzer.analyze_symbol('SP500', analysis_date='1987-10-18')

# 2000年ドットコムバブル頂点での分析
analyzer.analyze_symbol('NASDAQCOM', analysis_date='2000-03-10')

# 2008年リーマンショック前の分析
analyzer.analyze_symbol('SP500', analysis_date='2008-09-14')
```

### 3. コマンドラインからの実行

```bash
# 全履歴データのダウンロード
python entry_points/main.py market-data download --full-history --symbols SP500 NASDAQCOM

# 過去の特定日でのFCO分析
python entry_points/main.py fco analyze --symbol SP500 --date 1987-10-18

# 履歴的クラッシュ期間の包括分析
python entry_points/main.py fco historical-crashes --analyze
```

## 📊 パフォーマンス特性

### データサイズとアクセス速度

| データ範囲 | ファイルサイズ | 読込時間 | 用途 |
|----------|------------|---------|------|
| 2年 (500日) | ~10 KB | ~1.6ms | 日常分析 |
| 10年 (2,500日) | ~50 KB | ~1.8ms | 中期分析 |
| 40年 (10,000日) | ~1 MB | ~2.1ms | 全履歴分析 |

**結論**: 40年分の全履歴データでも読込時間への影響は無視できるレベル

### メモリ使用量

- 81銘柄の全履歴（40年分）: 約40MB
- 単一銘柄の全履歴: 約0.5MB
- FCO分析時の一時メモリ: 約100MB（126窓×750日）

## 🔄 データ更新戦略

### 日次更新フロー

```python
# 毎日実行するスケジュール更新
def daily_update():
    downloader = MarketDataDownloader(use_full_history=True)
    
    # 最新データのみ差分更新
    downloader.update_latest_data()
    
    # FCO分析を実行
    analyzer = FCODailyAnalyzer(use_full_history=True)
    analyzer.run_daily_analysis()
```

### 初期データ構築

```python
# 初回のみ：全銘柄の全履歴を取得
def initial_setup():
    downloader = MarketDataDownloader(use_full_history=True)
    
    # カタログの全銘柄をダウンロード
    results = downloader.download_all_symbols(download_full=True)
    
    # 統計情報を確認
    stats = downloader.get_data_stats()
    print(f"全履歴データ: {stats['cached_symbols_full']}銘柄")
    print(f"合計サイズ: {stats['total_size_mb_full']} MB")
```

## 🎯 歴史的クラッシュ分析

### 主要クラッシュ日付

| イベント | 日付 | 銘柄 | 分析ウィンドウ |
|---------|------|------|--------------|
| ブラックマンデー | 1987-10-19 | SP500 | 1985-05 ~ 1987-10 |
| アジア通貨危機 | 1997-10-27 | SP500 | 1995-05 ~ 1997-10 |
| ドットコムバブル | 2000-03-10 | NASDAQCOM | 1997-11 ~ 2000-03 |
| 9.11テロ | 2001-09-17 | SP500 | 1999-03 ~ 2001-09 |
| リーマンショック | 2008-09-15 | SP500 | 2006-03 ~ 2008-09 |
| コロナショック | 2020-03-23 | SP500 | 2017-11 ~ 2020-03 |

### 分析実行例

```python
def analyze_historical_crashes():
    analyzer = FCODailyAnalyzer(use_full_history=True)
    
    crashes = [
        ('SP500', '1987-10-18', 'ブラックマンデー前日'),
        ('NASDAQCOM', '2000-03-09', 'ドットコム頂点'),
        ('SP500', '2008-09-14', 'リーマン前日'),
        ('SP500', '2020-03-22', 'コロナ底値前日')
    ]
    
    for symbol, date, event in crashes:
        result = analyzer.analyze_symbol(symbol, date)
        print(f"{event}: DS-LPPLS = {result.ds_lppls_confidence:.2%}")
```

## 🛠️ トラブルシューティング

### よくある問題と解決策

1. **APIキーエラー**
   ```bash
   # .envファイルに設定
   FRED_API_KEY=your_key_here
   ALPHA_VANTAGE_KEY=your_key_here
   ```

2. **キャッシュが見つからない**
   ```python
   # キャッシュディレクトリを確認
   from pathlib import Path
   cache_dir = Path("data/market_data/cache/full")
   print(f"キャッシュ存在: {cache_dir.exists()}")
   print(f"ファイル数: {len(list(cache_dir.glob('*.parquet')))}")
   ```

3. **メモリ不足**
   ```python
   # 並列度を下げる
   engine = FCOEngine(use_parallel=True, max_workers=2)  # 4→2
   ```

## 📈 ダッシュボード統合

全履歴データは、Streamlitダッシュボードで任意期間を選択して可視化できます：

```python
# ダッシュボードでの使用例
def load_full_history(symbol):
    cache_file = Path(f"data/market_data/cache/full/{symbol}_full.parquet")
    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        return df
    return None

# 期間フィルタリング
def filter_period(df, start_date, end_date):
    return df[(df.index >= start_date) & (df.index <= end_date)]
```

## 🔮 今後の拡張計画

1. **自動クラッシュ検出**
   - 全履歴データをスキャンして潜在的クラッシュを自動検出

2. **比較分析**
   - 複数の歴史的クラッシュのパターン比較

3. **機械学習統合**
   - 全履歴データを使用した予測モデルの訓練

4. **リアルタイム更新**
   - WebSocketによる日中データの即時反映

## 📝 まとめ

全履歴データアーキテクチャにより、以下が実現されました：

- ✅ **40年分の市場データを効率的に管理**（~1MB/銘柄）
- ✅ **歴史的クラッシュの包括的分析**
- ✅ **ミリ秒レベルのアクセス速度**（2.1ms）
- ✅ **柔軟な期間選択と可視化**
- ✅ **既存システムとの完全な互換性**

これにより、FCO v2.0は真に包括的な市場分析プラットフォームとなりました。
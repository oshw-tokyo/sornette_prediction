# FCO全履歴データアーキテクチャ

## 📌 設計原則

FCOとLPPLは**完全に独立した分析システム**として設計されています。

### システム分離

| システム | データ要件 | キャッシュ | 用途 |
|---------|-----------|----------|------|
| **FCO** | 全履歴（40年） | `cache/full/{symbol}_full.parquet` | 歴史的クラッシュ分析・長期トレンド |
| **LPPL** | 2年分 | `cache/prepared/{symbol}_2y.parquet` | 日常的な市場監視・短期予測 |

### なぜ分離するのか

1. **分析手法の違い**
   - FCO: 126個の時間窓での多重分析、長期的視点
   - LPPL: 単一窓での精密フィッティング、短期的視点

2. **データ要件の違い**
   - FCO: 歴史的クラッシュ（1987, 2000, 2008）の分析に全履歴必須
   - LPPL: 最大750日（約2年）のデータで十分

3. **運用頻度の違い**
   - FCO: 日次または週次の包括的分析
   - LPPL: リアルタイム監視、高頻度更新

4. **将来の拡張性**
   - FCOとLPPLの独立進化が可能
   - 相互影響なしでアップグレード可能

## 🏗️ 実装アーキテクチャ

### データフロー

```
[Market Data Sources]
        ↓
[MarketDataDownloader]
    ├─[for_fco=True]→ cache/full/ (全履歴)
    └─[for_fco=False]→ cache/prepared/ (2年)
        ↓                    ↓
[FCODailyAnalyzer]    [LPPL Analyzer]
    ↓                    ↓
[FCO Dashboard]      [LPPL Dashboard]
```

### クラス設計

#### MarketDataDownloader
```python
class MarketDataDownloader:
    def __init__(self, for_fco: bool = True):
        """
        Args:
            for_fco: True = FCO用全履歴、False = LPPL用2年
        """
        self.for_fco = for_fco
        if for_fco:
            # 全履歴をダウンロード・保存
        else:
            # 2年分をダウンロード・保存
```

#### FCODailyAnalyzer
```python
class FCODailyAnalyzer:
    def __init__(self):
        """FCO専用アナライザー（全履歴のみ使用）"""
        self.full_cache_dir = Path("data/market_data/cache/full")
        # 2年キャッシュは参照しない
```

## 📊 パフォーマンス特性

### ストレージ効率

| データ範囲 | ファイルサイズ | 用途 |
|-----------|--------------|------|
| 2年（LPPL） | ~10KB/銘柄 | 81銘柄で約1MB |
| 40年（FCO） | ~1MB/銘柄 | 81銘柄で約40MB |

### アクセス速度

| 操作 | 2年キャッシュ | 全履歴キャッシュ |
|-----|-------------|---------------|
| 読込時間 | ~1.6ms | ~2.1ms |
| 差分 | - | +0.5ms（無視できる） |

## 🚀 使用方法

### FCO分析（全履歴）

```python
# データダウンロード
from infrastructure.market_data.data_downloader import MarketDataDownloader
downloader = MarketDataDownloader(for_fco=True)
downloader.download_symbol_data('SP500', download_full=True)

# FCO分析
from applications.analysis_tools.fco_daily_analyzer import FCODailyAnalyzer
analyzer = FCODailyAnalyzer()  # 全履歴のみ使用
analyzer.analyze_symbol('SP500')
```

### LPPL分析（2年）

```python
# データダウンロード
downloader = MarketDataDownloader(for_fco=False)
downloader.download_symbol_data('SP500', years=2)

# LPPL分析（既存システム）
# 既存のLPPLシステムがそのまま動作
```

## ✅ メリット

1. **明確な責任分離**: FCOとLPPLが相互に影響しない
2. **最適化**: 各システムが必要なデータのみ保持
3. **移行の安全性**: 既存LPPLシステムに影響なし
4. **将来性**: 独立した進化が可能

## 📝 まとめ

- FCO = 全履歴専用
- LPPL = 2年データ専用
- 完全分離により安定性と拡張性を両立
- パフォーマンス影響は実質ゼロ（+0.5ms）
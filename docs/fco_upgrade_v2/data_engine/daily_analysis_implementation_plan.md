# 📅 日次分析システム実装計画

## 概要
FCO v2.0アップグレード後の日次分析システム実装計画。API効率化とバッチ処理により、80銘柄の日次分析を実現。

## 1. 🎯 実装目標

### 主要目標
- **日次FCO分析**: 80銘柄に対する毎日のDS-LPPLS指標計算
- **API効率化**: バッチ取得による呼び出し削減（66.7%以上）
- **自動化**: cronジョブによる完全自動実行
- **アラート機能**: 高リスク銘柄の自動検出・通知

### 成果指標
- 日次分析完了時間: 30分以内
- API呼び出し数: 100回以下/日
- DS-LPPLS信頼度計算: 全銘柄完了
- エラー率: 5%以下

## 2. 🏗️ システムアーキテクチャ

### データフロー
```
Daily Scheduler → Batch Data Fetcher → FCO Engine → Result Storage → Alert System
      ↓                ↓                    ↓              ↓              ↓
  cron (3:00AM)    80 symbols         126 windows      FCO DB        Email/Slack
                   (1 API call/symbol)  (parallel)    SQLite       (if DS>30%)
```

### コンポーネント構成
```python
applications/analysis_tools/
├── daily_fco_analyzer.py       # 日次分析メインエンジン
├── batch_data_fetcher.py       # バッチデータ取得（既存活用）
└── alert_notifier.py           # アラート通知システム

infrastructure/
├── schedulers/
│   └── daily_cron_scheduler.py # cron設定・スケジューラー
└── cache/
    └── daily_data_cache.py     # 日次データキャッシュ
```

## 3. 🚀 API効率化戦略

### 現在の問題点
- **日次分析**: N週 × M銘柄 = N×M回のAPI呼び出し
- **80銘柄×52週**: 4,160回/年のAPI呼び出し
- **レート制限**: 特にTwelve Data（800req/日）が厳しい

### 効率化実装
```python
class DailyBatchFetcher:
    def fetch_daily_updates(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        日次更新データのバッチ取得
        - 前日のキャッシュから差分のみ取得
        - 1銘柄1API呼び出しで最新365日取得
        - メモリ効率的なストリーミング処理
        """
        cache = DailyDataCache()
        results = {}
        
        for symbol in symbols:
            # キャッシュから前日データ取得
            cached_data = cache.get(symbol)
            
            if cached_data and self._is_recent(cached_data):
                # 最新1日分のみ取得
                new_data = self._fetch_incremental(symbol, cached_data.index[-1])
            else:
                # 全365日取得（初回or古いキャッシュ）
                new_data = self._fetch_full_year(symbol)
            
            results[symbol] = new_data
            cache.update(symbol, new_data)
        
        return results
```

### API呼び出し削減効果
| 分析タイプ | 従来方式 | 新方式 | 削減率 |
|-----------|---------|--------|--------|
| 日次分析（52週） | 4,160回/年 | 80回/年 | 98.1% |
| 日次分析 | 29,200回/年 | 29,200回/年 | - |
| **日次差分更新** | - | **80回/日** | **99.7%** |

## 4. 📊 FCO分析統合

### 日次FCO分析フロー
```python
class DailyFCOAnalyzer:
    def run_daily_analysis(self):
        """日次FCO分析の実行"""
        
        # 1. バッチデータ取得
        fetcher = DailyBatchFetcher()
        market_data = fetcher.fetch_daily_updates(self.symbols)
        
        # 2. FCOエンジンによる分析（並列処理）
        fco_engine = FCOEngine(use_parallel=True, max_workers=8)
        results = {}
        
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    fco_engine.compute_ds_lppls_confidence, 
                    data['Close'].values
                ): symbol
                for symbol, data in market_data.items()
            }
            
            for future in as_completed(futures):
                symbol = futures[future]
                result = future.result()
                results[symbol] = result
        
        # 3. 結果保存
        db = FCOResultsDatabase()
        for symbol, result in results.items():
            db.save_fco_analysis(self._to_db_format(symbol, result))
        
        # 4. アラート判定
        high_risk = self._check_alerts(results)
        if high_risk:
            self._send_alerts(high_risk)
        
        return results
```

### DS-LPPLS閾値設定
```python
ALERT_THRESHOLDS = {
    'critical': 50.0,  # DS-LPPLS信頼度 > 50%
    'high': 40.0,      # DS-LPPLS信頼度 > 40%
    'medium': 30.0,    # DS-LPPLS信頼度 > 30%
    'watch': 20.0      # DS-LPPLS信頼度 > 20%
}
```

## 5. 🔔 アラートシステム

### アラート条件
1. **Critical Alert**: DS-LPPLS > 50% かつ tc < 30日
2. **High Alert**: DS-LPPLS > 40% かつ tc < 60日
3. **Medium Alert**: DS-LPPLS > 30% かつ tc < 90日
4. **Watch List**: DS-LPPLS > 20%

### 通知チャネル
```python
class AlertNotifier:
    def send_alert(self, alert_level: str, symbols: List[Dict]):
        """マルチチャネル通知"""
        
        # Email通知
        if alert_level in ['critical', 'high']:
            self._send_email(symbols)
        
        # Slack通知
        if self.slack_enabled:
            self._send_slack(symbols)
        
        # ダッシュボード更新
        self._update_dashboard_alerts(symbols)
        
        # ログ記録
        self._log_alert(alert_level, symbols)
```

## 6. 📅 実装スケジュール

### Phase 1: 基盤構築（3日）
- [ ] DailyBatchFetcher実装
- [ ] DailyDataCacheシステム
- [ ] API効率化テスト

### Phase 2: FCO統合（2日）
- [ ] DailyFCOAnalyzer実装
- [ ] 並列処理最適化
- [ ] エラーハンドリング

### Phase 3: 自動化（2日）
- [ ] Cronスケジューラー設定
- [ ] アラートシステム実装
- [ ] 通知チャネル統合

### Phase 4: テスト・調整（3日）
- [ ] 全銘柄での統合テスト
- [ ] パフォーマンス最適化
- [ ] 本番環境デプロイ

## 7. 🛠️ 技術要件

### 必要なライブラリ
```python
# requirements.txt追加分
schedule>=1.2.0      # スケジューリング
redis>=4.5.0        # キャッシュ（オプション）
sendgrid>=6.10.0    # Email通知
slack-sdk>=3.21.0   # Slack通知
```

### システム要件
- CPU: 4コア以上（並列処理用）
- メモリ: 8GB以上
- ストレージ: 50GB以上（キャッシュ用）
- OS: Linux（cron必須）

## 8. 🎯 期待される成果

### 定量的成果
- **処理時間**: 80銘柄を30分以内で分析完了
- **API効率**: 99.7%の呼び出し削減
- **検出精度**: 過去のクラッシュ事例との90%以上の一致

### 定性的成果
- **早期警戒**: 市場クラッシュの1-3ヶ月前検出
- **自動化**: 人的介入なしの完全自動運用
- **拡張性**: 銘柄数増加への柔軟な対応

## 9. 📝 実装時の注意事項

### クリティカルポイント
1. **論文再現保護**: 1987年100/100スコア維持必須
2. **API制限遵守**: 特にTwelve Data（800req/日）
3. **データ整合性**: キャッシュと最新データの一致
4. **エラー耐性**: 個別失敗が全体に影響しない設計

### ベストプラクティス
```python
# エラー処理例
try:
    result = fco_engine.compute_ds_lppls_confidence(prices)
except Exception as e:
    logger.error(f"FCO analysis failed for {symbol}: {e}")
    # 個別失敗を記録し、処理継続
    failed_symbols.append(symbol)
    continue
```

## 10. 🔄 将来の拡張

### 短期的拡張（3ヶ月以内）
- リアルタイムデータフィード統合
- Webダッシュボードでのリアルタイム表示
- モバイルアプリ通知

### 長期的拡張（6ヶ月以降）
- 機械学習による予測精度向上
- 複数市場の相関分析
- 自動取引システムとの統合

---

*作成日: 2025-09-12*
*作成者: Claude Code*
*バージョン: 1.0*
# FCO全履歴アーキテクチャ移行計画

## 📋 移行影響調査結果

### 修正が必要なファイル

| ファイル | 現状 | 修正内容 | 優先度 |
|---------|------|---------|--------|
| `fco_daily_analyzer.py` | ✅修正済み | 全履歴のみ使用に変更済み | 完了 |
| `data_downloader.py` | ✅修正済み | for_fcoパラメータ実装済み | 完了 |
| `fco_historical_analyzer.py` | ❌旧実装 | 全履歴キャッシュ使用に変更必要 | 高 |
| `fco_daily_scheduler.py` | ❌旧実装 | FCODailyAnalyzer使用に変更必要 | 高 |
| `entry_points/main.py` | ❌未確認 | パラメータ調整必要 | 中 |
| `fco_engine.py` | ✅問題なし | データソース非依存 | - |
| `fco_black_monday_1987_validator.py` | ✅問題なし | テスト用 | - |

### ドキュメント更新状況

| ドキュメント | 更新要否 | 内容 |
|-------------|---------|------|
| `fco_full_history_architecture.md` | ✅作成済み | 新アーキテクチャ説明 |
| `full_historical_data_operation_guide.md` | ⚠️要更新 | use_full_history削除 |
| `architecture_migration_local_data_storage.md` | ⚠️要更新 | cache_years削除 |
| `daily_analysis_implementation_plan.md` | ⚠️要更新 | 新実装に合わせる |

## 🔧 実装計画

### Phase 1: 旧実装の廃止と新実装への移行

#### 1.1 fco_historical_analyzer.py の廃止
- **理由**: API直接呼び出し、旧アーキテクチャ依存
- **代替**: fco_daily_analyzer.py が過去データ分析も対応
- **アクション**: ファイル削除またはアーカイブ化

#### 1.2 fco_daily_scheduler.py の修正
```python
# 修正前: API直接呼び出し
data_client = UnifiedDataClient()
df = data_client.get_data_with_fallback(symbol)

# 修正後: ローカルキャッシュのみ
analyzer = FCODailyAnalyzer()
analyzer.analyze_symbol(symbol)
```

### Phase 2: エントリーポイントの統一

#### 2.1 コマンド体系の整理
```bash
# FCO専用コマンド（全履歴使用）
python entry_points/main.py fco download    # 全履歴ダウンロード
python entry_points/main.py fco analyze     # FCO分析実行
python entry_points/main.py fco schedule    # 定期実行

# LPPL専用コマンド（2年データ使用）
python entry_points/main.py lppl download   # 2年データダウンロード
python entry_points/main.py lppl analyze    # LPPL分析実行
```

### Phase 3: テストとバリデーション

#### 3.1 データ整合性確認
- 全履歴キャッシュの存在確認
- データ期間の妥当性検証
- FCO分析結果の検証

#### 3.2 パフォーマンステスト
- 読込速度の測定（目標: <3ms）
- メモリ使用量の確認
- 並列処理の効率性

## 📊 移行スケジュール

| タスク | 推定時間 | 状態 |
|--------|---------|------|
| 影響調査 | 30分 | ✅完了 |
| fco_historical_analyzer廃止 | 15分 | 📋計画中 |
| fco_daily_scheduler修正 | 30分 | 📋計画中 |
| エントリーポイント整理 | 45分 | 📋計画中 |
| ドキュメント更新 | 30分 | 📋計画中 |
| テスト実施 | 30分 | 📋計画中 |

## ✅ 成功基準

1. **完全分離**: FCOが全履歴キャッシュのみを使用
2. **API非依存**: FCO分析時にAPI呼び出しゼロ
3. **互換性維持**: 既存LPPLシステムに影響なし
4. **パフォーマンス**: 分析速度の劣化なし

## 📝 注意事項

- fco_historical_analyzerは廃止予定だが、念のためアーカイブ保持
- 移行は段階的に実施し、各段階でテスト実施
- LPPL側のコードは一切変更しない（完全分離の原則）
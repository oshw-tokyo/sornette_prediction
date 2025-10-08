# 旧LPPLスケジューラー関連文書アーカイブ

**アーカイブ日**: 2025-10-08
**理由**: FCO v2.1へのシステム移行に伴い、旧LPPL定期解析システム関連文書を整理

---

## 📁 アーカイブ文書

### 1. scheduled_analysis_requirements.md (343行)
**元の場所**: `docs/scheduled_analysis_requirements.md`
**内容**: 旧LPPL定期スケジュール分析システムの実装完了報告書（2025-08-05実装完了）
**アーカイブ理由**:
- FCO v2.1では`fco-daily`コマンドによる日次分析が主流
- `scheduled-analysis`コマンドは実装されているが、旧システム扱い
- 実装報告書としての役割は終了

**主要内容**:
- Source×Frequency分離設計 (fred_weekly, alpha_vantage_daily)
- 曜日整合性確保システム
- 自動バックフィル機能
- LPPL分析基準日の理論的基盤

---

### 2. schedule_command_specification.md (268行)
**元の場所**: `docs/schedule_command_specification.md`
**内容**: `scheduled-analysis`コマンドの動作仕様書
**アーカイブ理由**:
- 旧LPPLスケジューラーのコマンド仕様
- FCO v2.1では`fco-daily`コマンドが推奨される
- コマンド自体は残っているが、メンテナンスは非推奨

**主要内容**:
- コマンドラインインターフェース仕様
- バックフィル機能の詳細
- 曜日自動調整ロジック

---

## 🔄 現在のシステム

**FCO日次分析システム**:
- **コマンド**: `python entry_points/main.py fco-daily`
- **文書**: `docs/fco_daily_scheduler_usage.md`（保持）
- **特徴**: FCO v2.1の126窓多重時間窓分析に対応

**推奨される定期解析方法**:
```bash
# FCO日次分析（推奨）
python entry_points/main.py fco-daily run

# 旧LPPL定期解析（非推奨）
python entry_points/main.py scheduled-analysis run
```

---

## 📚 参照目的

これらの文書は以下の目的で保存されています：

1. **歴史的記録**: 旧LPPLスケジューラーの設計思想・実装詳細の記録
2. **理論的参考**: 分析基準日の考え方、曜日整合性の重要性など
3. **移行参考**: FCO v2.1への移行過程での参照資料
4. **コマンド仕様**: `scheduled-analysis`コマンドが残っている場合の参照

---

## ⚠️ 注意事項

- **新規実装**: FCO v2.1システムを使用してください
- **旧コマンド使用**: `scheduled-analysis`コマンドは動作しますが、FCOシステムとの統合は不完全です
- **文書更新**: これらのアーカイブ文書は更新されません

---

*アーカイブ作成者: Claude Code*
*アーカイブ日時: 2025-10-08*

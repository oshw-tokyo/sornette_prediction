# 未使用コード分析レポート

## 🎯 分析目的

排他的API設計への変更により、未使用となったコードを特定し、クリーンアップ戦略を提案する。

---

## 📊 分析結果概要

### **変更による影響範囲**
- **主要変更**: フォールバック機能の除去 → 排他的API割り当て設計
- **対象ファイル**: 15個のファイルで"fallback"文字列を検出
- **直接クライアント使用**: 20個のファイルでFREDDataClient()直接使用を検出

---

## 🚨 即座に修正が必要なファイル

### **1. 現在アクティブなファイル（統合データクライアント使用に要更新）**

| ファイル | 状況 | 優先度 | 修正内容 |
|---------|------|--------|----------|
| `applications/examples/validation_demo.py` | ❌ FRED直接使用 | **🔴 高** | UnifiedDataClient使用に変更 |
| `infrastructure/data_sources/market_data_manager.py` | ❌ FRED直接使用 | **🟡 中** | 既存システムとの互換性確認後修正 |
| `infrastructure/monitoring/multi_market_monitor.py` | ❌ FRED直接使用 | **🟡 中** | UnifiedDataClient使用に変更 |

### **2. 保護対象（変更禁止）**

| ファイル | 理由 | 対応 |
|---------|------|------|
| `core/validation/crash_validators/base_crash_validator.py` | 論文再現性保護 | **修正禁止** - 既存のまま維持 |
| `tests/historical_crashes/` 以下全て | テスト検証整合性 | **修正禁止** - 独立動作必要 |

---

## 📁 クリーンアップ対象ファイル

### **A. Archive済みファイル（削除対象外）**
```
archive/src_pre_migration_backup/
archive/root_files_backup/
dev_workspace/testing/
```
**対応**: 既にアーカイブされているため、クリーンアップ対象外

### **B. 未使用の可能性が高いファイル**

#### **1. スケジューラー関連（カタログベース統合により冗長化）**
- `applications/schedulers/` ディレクトリ全体
- **状況**: entry_points/main.pyによる統一実行により使用停止の可能性
- **確認必要**: 実際の使用状況調査

#### **2. 個別データクライアント（直接使用の削減対象）**
現在も必要だが、直接使用を統合データクライアント経由に変更すべきファイル：

| クライアント | 現在の使用状況 | 対応方針 |
|-------------|---------------|----------|
| `fred_data_client.py` | UnifiedDataClient内で使用 | **保持** - 間接使用 |
| `alpha_vantage_client.py` | UnifiedDataClient内で使用 | **保持** - 間接使用 |
| `coingecko_client.py` | UnifiedDataClient内で使用 | **保持** - 間接使用 |

---

## 🔧 推奨修正アクション

### **Phase 1: 緊急修正（即座実行）**

#### **1. validation_demo.py の修正**
```python
# 変更前（現在）
from infrastructure.data_sources.fred_data_client import FREDDataClient
client = FREDDataClient()

# 変更後（推奨）
from infrastructure.data_sources.unified_data_client import UnifiedDataClient
client = UnifiedDataClient()
data, source = client.get_data_with_fallback('NASDAQCOM', start, end)
```

#### **2. multi_market_monitor.py の修正**
```python
# 変更前
self.data_client = FREDDataClient()

# 変更後
self.data_client = UnifiedDataClient()
# メソッド呼び出しも対応する修正が必要
```

### **Phase 2: 詳細調査（1-2日以内）**

#### **1. market_data_manager.py の役割確認**
- 現在のシステムでの使用状況確認
- UnifiedDataClientとの重複機能の特定
- 統合または分離の判断

#### **2. 使用されていないスケジューラーファイルの特定**
```bash
# 使用状況調査コマンド例
grep -r "import.*schedulers" --include="*.py" .
grep -r "from.*schedulers" --include="*.py" .
```

### **Phase 3: クリーンアップ（1週間以内）**

#### **1. 未使用ファイルの削除**
確認後、使用されていないファイルの削除実行

#### **2. インポート整理**
使用されていないimport文の削除

---

## ⚡ 緊急修正スクリプト

### **validation_demo.py の自動修正**

```bash
# バックアップ作成
cp applications/examples/validation_demo.py applications/examples/validation_demo.py.backup

# 修正実行（sed使用）
sed -i 's/from infrastructure.data_sources.fred_data_client import FREDDataClient/from infrastructure.data_sources.unified_data_client import UnifiedDataClient/' applications/examples/validation_demo.py

sed -i 's/client = FREDDataClient()/unified_client = UnifiedDataClient()/' applications/examples/validation_demo.py

sed -i 's/data = client.get_series_data/data, source = unified_client.get_data_with_fallback/' applications/examples/validation_data.py
```

### **修正後テスト（必須）**
```bash
# 論文再現性確認（100/100スコア維持必須）
python entry_points/main.py validate --crash 1987

# 修正したファイルの動作確認
python applications/examples/validation_demo.py
```

---

## 📊 リスク評価

### **🔴 高リスク修正**
- **論文再現系ファイル**: 絶対に変更しない
- **テスト系ファイル**: 独立動作が必要なため慎重に判断

### **🟡 中リスク修正**
- **monitoring系ファイル**: 使用状況の詳細確認が必要
- **manager系ファイル**: 他システムとの依存関係調査必要

### **🟢 低リスク修正**
- **example系ファイル**: 単独動作のため修正容易
- **未使用ファイル**: 使用確認後の削除は安全

---

## 🔍 継続監視項目

### **依存関係追跡**
1. **月次レビュー**: 未使用import文の定期チェック
2. **リファクタリング時**: 影響範囲の事前評価
3. **新機能追加時**: 既存コードとの重複確認

### **自動化ツール候補**
```python
# 提案: 未使用コード検出ツール
def find_unused_imports():
    """未使用import文の自動検出"""
    pass

def analyze_function_usage():
    """未使用関数の自動検出"""
    pass
```

---

## 💡 長期改善提案

### **コード品質管理**
1. **pre-commit hooks**: 未使用import自動削除
2. **CI/CD統合**: コードカバレッジ監視
3. **依存関係可視化**: ツールによる自動生成

### **アーキテクチャクリーンアップ**
1. **レイヤー分離明確化**: 4層アーキテクチャの厳密化
2. **循環依存除去**: モジュール間の依存関係整理
3. **インターフェース統一**: 統合データクライアント経由の完全移行

---

**分析日**: 2025-08-09  
**分析者**: Claude Code  
**次回レビュー予定**: 2025-08-16
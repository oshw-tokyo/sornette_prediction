# ダッシュボード実装仕様書（実装状況ベース）

**更新日**: 2025-08-07  
**版数**: v1.0 (実装完了版)  
**メタ情報仕様**: [meta_information_specification.md](./meta_information_specification.md) に準拠

---

## 🎯 **概要**

**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

Symbol-Based Market Analysis Dashboard は、LPPL（Log-Periodic Power Law）モデルによる市場クラッシュ予測結果を可視化する Streamlit ベースのWebインターフェースです。現在完全実装済みで本番稼働中の主要機能として動作しています。

---

## 🏗️ **システム構造**

### **メインファイル**
**ファイル**: `applications/dashboards/main_dashboard.py`  
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🔗[DEPENDENT]`

- **行数**: 970行（2025-08-07現在）
- **主要クラス**: `SymbolAnalysisDashboard`
- **依存関係**: ResultsDatabase, UnifiedDataClient, Streamlit
- **起動方法**: `streamlit run applications/dashboards/main_dashboard.py`

### **自動初期化システム**
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `🔧[UTILITY]` `🏗️[FOUNDATION]`

```python
# .envファイル自動読み込み（Line 23-33）
from dotenv import load_dotenv
load_dotenv(dotenv_path)  # API認証情報の自動設定
```

**実装理由**: API認証エラーの防止とユーザビリティ向上  
**変更可否**: ❌ **変更禁止** - 他システムがこの動作に依存

---

## 📊 **3タブ構成システム**

### **Tab 1: Price & Predictions**
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

**機能**: 論文再現テスト右上グラフ相当の正規化LPPL可視化  
**実装メソッド**: `render_price_predictions_tab()` (Line 373-593)

#### **主要機能**
1. **正規化データ表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🏗️[FOUNDATION]`
   - **実装**: LPPL理論に基づく0-1正規化処理
   - **変更可否**: ❌ **変更禁止** - 科学的根幹のため

2. **複数予測線表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: tc値を実際の予測日に変換して縦線表示
   - **変更可否**: ✅ **変更可能** - 表示方法の改善可能

3. **価格データ取得システム**
   - **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `🎯[CORE]` `🔗[DEPENDENT]`
   - **実装**: UnifiedDataClient経由でFRED/Alpha Vantageから取得
   - **依存関係**: API認証、ネットワーク接続必須

#### **エラーハンドリング**
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔧[EVOLVING]` `🔧[UTILITY]` `🎯[ISOLATED]`

- データ取得失敗時の詳細診断表示
- API認証エラーの識別
- データベース情報のデバッグ表示
- **変更可否**: ✅ **改善推奨** - より詳細な診断情報追加可能

### **Tab 2: Prediction Convergence**  
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`

**機能**: 時系列での予測収束性分析  
**実装メソッド**: `render_prediction_convergence_tab()` (Line 594-702)

#### **実装状況**
- **時系列プロット**: `🟢[IMPLEMENTED]` - 予測日の変化を可視化
- **信頼度表示**: `🟢[IMPLEMENTED]` - R²値とQuality指標表示
- **統計サマリー**: `🟢[IMPLEMENTED]` - 平均値・高品質データ数表示

**データ検証結果**: NASDAQ COM で2データポイント確認済み（実際のデータ数を反映）

### **Tab 3: Parameters**
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

**機能**: LPPLパラメータとメタデータの詳細表示  
**実装メソッド**: `render_parameters_tab()` (Line 703-904)

#### **重要な実装改善**
1. **フィッティング基準日表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🏗️[FOUNDATION]`
   - **実装**: `analysis_basis_date` を優先表示（Analysis Date に代替）
   - **変更可否**: ❌ **変更禁止** - 分析基準日概念の根幹

2. **データ期間日数表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: 期間範囲表示から日数表示へ変更
   - **変更可否**: ✅ **変更可能** - 表示形式の改善可能

3. **Quality/Confidence並列表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: 隣接列に配置、説明テキスト追加
   - **変更可否**: ✅ **変更可能** - UI改善可能

4. **メトリクス定義説明**
   - **メタ情報**: `🟢[IMPLEMENTED]` `📝[LOW]` `🔧[EVOLVING]` `🔧[UTILITY]` `🎯[ISOLATED]`
   - **実装**: Quality/Confidenceの詳細説明表示
   - **変更可否**: ✅ **変更推奨** - より詳しい説明追加可能

---

## 🔧 **技術実装詳細**

### **データフロー**
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `🎯[CORE]` `🔗[DEPENDENT]`

```
1. データベース読み込み (ResultsDatabase)
   ↓
2. 銘柄選択 (サイドバー)
   ↓  
3. 生データ取得 (UnifiedDataClient)
   ↓
4. LPPL計算・可視化 (compute_lppl_fit)
   ↓
5. 3タブ表示 (Streamlit)
```

### **LPPL計算エンジン**
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🏗️[FOUNDATION]`

**実装メソッド**: `compute_lppl_fit()` (Line 286-357)

```python
# 重要な数式実装（変更禁止）
fitted_log_prices = A + B * tau_power_beta + C * tau_power_beta * oscillation
normalized_prices = (prices - price_min) / (price_max - price_min)
```

**科学的根拠**: Sornette理論のLPPLモデルに基づく  
**変更可否**: ❌ **変更厳禁** - 論文再現の根幹のため

### **日付変換システム**
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`

**実装メソッド**: `convert_tc_to_real_date()` (Line 358-372)

```python
# tc値を実際の予測日に変換
if tc > 1:
    days_beyond_end = (tc - 1) * total_days
    prediction_date = end_dt + timedelta(days=days_beyond_end)
```

**変更可否**: ✅ **変更可能** - アルゴリズム改善可能

---

## 🎨 **UI/UX設計**

### **サイドバー機能**
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`

1. **銘柄選択**: 市場カタログベース選択
2. **表示件数**: デフォルト5件、最大20件
3. **品質フィルター**: high_quality のみ表示オプション

### **カラーテーマ**
**メタ情報**: `🟢[IMPLEMENTED]` `📝[LOW]` `🔧[EVOLVING]` `🔧[UTILITY]` `🎯[ISOLATED]`

- **主要色**: 青系（市場データ）、赤系（LPPL予測）
- **アクセント**: 緑系（予測線）
- **変更可否**: ✅ **変更可能** - ブランディング対応可能

### **レスポンシブ対応**
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔒[STABLE]` `⚙️[FEATURE]` `🎯[ISOLATED]`

- Streamlit標準の`use_container_width=True`使用
- ワイドレイアウト設定済み

---

## ⚠️ **制限事項と今後の拡張**

### **未実装機能**
**メタ情報**: `🔴[TODO]` `📋[MEDIUM]` `🧪[EXPERIMENTAL]` `⚙️[FEATURE]` `🎯[ISOLATED]`

1. **タイムゾーン選択機能**
   - **現状**: UTC固定表示
   - **必要性**: 中程度
   - **実装優先度**: 低

2. **リアルタイム更新**
   - **現状**: 手動リフレッシュ
   - **必要性**: 低
   - **理由**: スケジュール分析システムで代替

### **パフォーマンス制限**
**メタ情報**: `🟡[PARTIAL]` `📋[MEDIUM]` `🔧[EVOLVING]` `🔧[UTILITY]` `🔗[DEPENDENT]`

1. **データ取得速度**: API制限に依存（2-5秒）
2. **表示データ量**: 最大20件に制限
3. **変更可否**: ✅ **最適化可能** - キャッシュ機能追加可能

### **依存関係リスク**
**メタ情報**: `🟡[PARTIAL]` `⭐[HIGH]` `🔧[EVOLVING]` `🎯[CORE]` `🔗[DEPENDENT]`

1. **外部API**: FRED/Alpha Vantage の可用性に依存
2. **データベース**: SQLite ファイルの整合性に依存
3. **対策**: エラーハンドリング強化済み

---

## 🔄 **メンテナンス指針**

### **変更禁止領域**
**メタ情報**: `🔒[STABLE]` `🔥[CRITICAL]`

1. **LPPL数式実装**: `compute_lppl_fit()` の数学的計算部分
2. **分析基準日概念**: `analysis_basis_date` の使用方法
3. **データベーススキーマ**: 既存カラムの意味変更

### **改善推奨領域**
**メタ情報**: `🔧[EVOLVING]` `⚙️[FEATURE]`

1. **エラー表示**: より詳細な診断情報
2. **UI改善**: 色彩・レイアウト最適化
3. **パフォーマンス**: キャッシュ・非同期処理

### **実験可能領域**
**メタ情報**: `🧪[EXPERIMENTAL]` `📝[LOW]`

1. **新しい可視化**: 追加のグラフ種類
2. **インタラクション**: ユーザー操作機能
3. **エクスポート**: CSV/PDF出力機能

---

## 📋 **更新履歴**

| 日付 | 版数 | 更新内容 | 影響度 |
|------|------|----------|--------|
| 2025-08-07 | v1.0 | 実装完了版作成、メタ情報導入 | 🔥[CRITICAL] |
| 2025-08-06 | - | Parameters タブ改善（フィッティング基準日対応） | ⭐[HIGH] |
| 2025-08-05 | - | Price & Predictions タブ復旧完了 | ⭐[HIGH] |

---

## 🏷️ **関連ドキュメント**

- **設計思想**: [implementation_strategy.md](./implementation_strategy.md)
- **メタ情報仕様**: [meta_information_specification.md](./meta_information_specification.md)
- **分析基準日概念**: [CLAUDE.md](../CLAUDE.md#分析基準日-analysis-basis-date-の定義)
- **進捗管理**: [progress_management/CURRENT_PROGRESS.md](./progress_management/CURRENT_PROGRESS.md)
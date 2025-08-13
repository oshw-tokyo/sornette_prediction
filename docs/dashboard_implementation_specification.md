# ダッシュボード実装仕様書（実装状況ベース）

**更新日**: 2025-08-07 (最終更新: 2025-08-11)  
**版数**: v1.1 (Symbol Filters Architecture v2 実装完了版)  
**メタ情報仕様**: [meta_information_specification.md](./meta_information_specification.md) に準拠

---

## 🎯 **概要**

**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `⚙️[FEATURE]` `🎯[CORE]`

Symbol-Based Market Analysis Dashboard は、LPPL（Log-Periodic Power Law）モデルによる市場クラッシュ予測結果を可視化する Streamlit ベースのWebインターフェースです。**Symbol Filters Architecture v2 (2025-08-11実装)**により、銘柄選択・データアクセス・期間制御の完全分離を実現し、直感的で予測可能なユーザー体験を提供します。

### 🆕 **v1.1の主要革新** (2025-08-11)
- **Symbol Filters**: 銘柄選択リストのみに影響、データ取得から完全分離
- **Apply Button制御**: 明示的な更新制御による予測可能な動作
- **Currently Selected Symbol**: リアルタイム選択状態表示
- **Displaying Period**: プロット範囲のみ制御、全データアクセス保証

---

## 🏗️ **システム構造**

### **メインファイル**
**ファイル**: `applications/dashboards/main_dashboard.py`  
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🔗[DEPENDENT]`

- **行数**: 3,100行+ （2025-08-11現在 - Symbol Filters Architecture v2実装）
- **主要クラス**: `SymbolAnalysisDashboard`
- **主要メソッド**: `render_sidebar_v2()`, `get_symbol_analysis_data()`, `_get_filtered_symbols()`
- **依存関係**: ResultsDatabase, UnifiedDataClient, Streamlit
- **起動方法**: `python entry_points/main.py dashboard` (統一エントリーポイント経由)

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

## 🎛️ **Symbol Filters Architecture v2 実装** (2025-08-11)

### **完全分離設計原則**
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🏗️[FOUNDATION]`

```
Symbol Filters → Symbol Selection → Apply → ALL Data Access → Display Period Filtering
     ↓               ↓            ↓           ↓                    ↓
銘柄リスト絞り込み → 銘柄選択 → 明示的実行 → 全履歴データ → プロット範囲制御
```

### **Symbol Filters** 🎛️
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`

**実装メソッド**: `render_sidebar_v2()` (Line 577-722)

#### **Asset Category**
- **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🎯[ISOLATED]`
- **機能**: 最上段配置、カテゴリベース銘柄絞り込み
- **実装**: `st.selectbox()` + カテゴリマスタ連携
- **変更可否**: ✅ **変更可能** - カテゴリ追加・UI改善可能

#### **Filter Conditions**
- **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🎯[ISOLATED]`
- **プリセットフィルター**: 9種類の事前定義設定
- **カスタムフィルター**: R²値・信頼度・使用可能性による多条件AND検索
- **リアルタイム更新**: 条件変更時に利用可能銘柄リスト即座更新

### **Symbol Selection & Status** 📈
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

#### **Choose Symbol**
- **実装**: `st.selectbox()` + `_get_filtered_symbols()` 連携
- **動作**: フィルタ結果からのリアルタイム選択
- **データアクセス**: 選択後に全履歴データ保証 (`limit=None`)

#### **Currently Selected Symbol**
- **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
- **実装**: `st.session_state` + `st.rerun()` によるリアルタイム状態表示
- **状態表示**: 
  - 🔵 "Ready to Apply" (選択済み・未適用)
  - 🟢 "Active" (適用済み・分析中)
  - ℹ️ "No symbol selected yet" (未選択)

### **Period & Execution Control** 📅
**メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

#### **Displaying Period**
- **実装メソッド**: `_get_period_selection()` (Line 783-836)
- **機能**: Symbol選択後にプロット範囲のみ制御
- **データ独立性**: 取得済み全データからの表示範囲抽出
- **エラーハンドリング**: Symbol未選択時の適切なガイダンス表示

#### **Apply Filters Button**
- **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `🔥[CRITICAL]` `⚙️[FEATURE]` `🎯[CORE]`
- **実装**: `st.button()` + 状態管理による明示的制御
- **動作**: Symbol選択時のみ有効化、未選択時は "Select Symbol First" 表示
- **変更可否**: ❌ **変更禁止** - UX設計の根幹

---

## 📊 **3タブ構成システム**

### **Tab 1: LPPL Fitting Analysis** 📈
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔧[EVOLVING]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

**機能**: 論文再現テスト相当の包括的LPPL分析可視化  
**実装メソッド**: `render_price_predictions_tab()` (Line 1400-1850+)

#### **主要機能 (2025-08-11拡張)**
1. **Latest Analysis Details**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[ENHANCED]` `⭐[HIGH]` `⚙️[FEATURE]` `🔗[DEPENDENT]`
   - **実装**: Display Period範囲内での最新フィッティング結果詳細表示
   - **変更可否**: ✅ **変更可能** - 表示項目・形式改善可能

2. **Integrated Predictions**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: Display Period範囲内の全分析結果による予測統合表示
   - **機能**: Latest Analysis基準による期間内の全予測日統合
   - **変更可否**: ✅ **変更可能** - 統合ロジック・可視化改善可能

3. **Individual Results**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🔧[ENHANCED]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: 期間選択と完全連動、基準日順での個別分析結果表示
   - **最大表示**: 5件制限（パフォーマンス考慮）
   - **変更可否**: ✅ **変更可能** - 表示件数・詳細度調整可能

4. **Future Period表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `⭐[HIGH]` `🔒[STABLE]` `⚙️[FEATURE]` `🏗️[FOUNDATION]`
   - **実装**: 拡張LPPL計算による予測期間可視化
   - **変更可否**: ❌ **変更禁止** - 科学的根幹のため

#### **エラーハンドリング**
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔧[EVOLVING]` `🔧[UTILITY]` `🎯[ISOLATED]`

- データ取得失敗時の詳細診断表示
- API認証エラーの識別
- データベース情報のデバッグ表示
- **変更可否**: ✅ **改善推奨** - より詳細な診断情報追加可能

### **Tab 2: Prediction Convergence** 📊
**メタ情報**: `🟢[IMPLEMENTED]` `🔧[ENHANCED]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[CORE]`

**機能**: 多期間収束分析による予測信頼性評価  
**実装メソッド**: `render_prediction_convergence_tab()` (Line 1850-2400+)

#### **2025-08-11大幅拡張**
1. **6期間タブシステム**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[CORE]`
   - **期間**: 1ヶ月/3ヶ月/半年/1年/2年/カスタム期間
   - **機能**: 各期間での収束分析・比較評価

2. **複数収束判定手法**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🏗️[FOUNDATION]`
   - **手法**: 標準偏差・重み付け・トレンド解析・コンセンサス予測
   - **実装**: `calculate_crash_date_convergence()` による科学的収束判定

3. **Multi-Period Convergence Analysis**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **機能**: 固定期間での標準化された時間窓による収束比較
   - **科学的意義**: 時系列予測の一致度による信頼性評価

#### **英語統一対応**
- **メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔒[STABLE]` `🔧[UTILITY]` `🎯[ISOLATED]`
- **実装**: 全UI要素の英語統一、国際対応準備完了

### **Tab 3: Parameters & References** 📋
**メタ情報**: `🟢[IMPLEMENTED]` `🔧[ENHANCED]` `⭐[HIGH]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

**機能**: LPPLパラメータ・メタデータ・参照情報の詳細表示  
**実装メソッド**: `render_parameters_tab()` (Line 2400-2900+)

### **Tab 4: Crash Prediction Clustering** 🎯 
**メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `🔥[CRITICAL]` `⚙️[FEATURE]` `🎯[CORE]`

**機能**: R²重み付きクラスタリングによる投資判断支援分析  
**実装メソッド**: `render_clustering_analysis_tab()` (Line 2900-3300+)  
**実装完了日**: 2025-08-13

#### **2025-08-13完全実装機能**
1. **期間選択UI**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: From/To日付選択、期間視覚化プログレスバー、自動範囲計算
   - **特徴**: Oldest/Latest Analysis情報表示、選択期間カバレッジ表示

2. **統合クラスタリングパラメータ設定**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[CORE]`
   - **距離パラメータ**: 10-90日（予測間の最大時間差）
   - **最小クラスタサイズ**: 2-20（初期値8、統計的最適値）
   - **将来予測期間**: 30-365日（可視化範囲）
   - **R²閾値**: 0.0-1.0（データ品質フィルター）

3. **R²重み付きクラスタリング手法**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `🔥[CRITICAL]` `⚙️[FEATURE]` `🏗️[FOUNDATION]`
   - **アルゴリズム**: DBSCAN 1D密度クラスタリング + R²品質重み付け
   - **重み付き平均**: 高R²予測に大きな影響力付与
   - **時系列非依存**: 純粋な品質ベース重み付け手法

4. **2次元インタラクティブ可視化**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **散布図**: フィッティング基準日 vs 予測クラッシュ日
   - **クラスター表示**: C1/C2形式、色分けによる識別
   - **中心線**: R²重み付き平均による水平線表示
   - **参照線**: Fitting Date = Crash Date基準線（対角線）
   - **ホバー情報**: クラスター詳細、重み付き統計値

5. **投資判断支援テーブル**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `🔥[CRITICAL]` `⚙️[FEATURE]` `🎯[CORE]`
   - **列順序**: Cluster → Weight Mean Date → Days to Crash → Days from Today → Weighted STD → STD → Size → Avg R² → Confidence
   - **本日からの日数**: 実用的投資判断指標
   - **信頼度評価**: High/Medium/Low自動判定
   - **推奨予測**: 最高信頼度クラスターの明示

6. **包括的ヘルプシステム**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `📋[MEDIUM]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **理論説明**: R²重み付き手法、クラスタリング原理
   - **パラメータガイド**: 各設定の意味と推奨値
   - **参照線解釈**: 投資タイミング判断方法

7. **統計的品質保証**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `🔧[UTILITY]` `🎯[CORE]`
   - **エラーハンドリング**: データ不足時の具体的解決策提示
   - **パラメータ最適化**: 統計的妥当性に基づくデフォルト値
   - **品質指標**: 総データ数、高品質データ数、クラスター統計

#### **投資判断支援の核心機能**
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🎯[CORE]` `💰[BUSINESS]`

- **予測統合**: 複数時期の分析結果を品質重み付きで統合
- **リスク評価**: クラスター信頼度による投資判断支援
- **タイミング指標**: 本日からの予測日数による緊急度評価
- **ポジション推奨**: 最高信頼度クラスターの明示表示

**変更可否**: ✅ **機能拡張推奨** - より多様な投資指標、リスク管理機能追加可能

#### **2025-08-11包括的機能拡張**
1. **フィッティング基準日ベース表示**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🏗️[FOUNDATION]`
   - **実装**: `analysis_basis_date` 優先表示による科学的正確性保証
   - **変更可否**: ❌ **変更禁止** - 分析基準日概念の根幹

2. **Prediction Summary**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[NEW]` `⭐[HIGH]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: Days to Crash等の予測期間指標表示
   - **機能**: 2指標による予測期間の明確化
   - **変更可否**: ✅ **変更可能** - 指標追加・計算方法改善可能

3. **参照情報拡張**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🆕[ENHANCED]` `📋[MEDIUM]` `⚙️[FEATURE]` `🎯[ISOLATED]`
   - **実装**: 1987年・2000年ドットコム参照追加による多様化
   - **機能**: 論文・理論的背景への包括的リンク
   - **変更可否**: ✅ **変更推奨** - 更多参照情報追加可能

4. **Multi-Period順序修正**
   - **メタ情報**: `🟢[IMPLEMENTED]` `🔧[FIXED]` `📋[MEDIUM]` `🔧[UTILITY]` `🎯[ISOLATED]`
   - **実装**: 期間順序の論理的整列による使いやすさ向上
   - **変更可否**: ✅ **変更可能** - UI配置・順序最適化可能

---

## 🔧 **技術実装詳細**

### **Symbol Filters Architecture v2 データフロー** (2025-08-11)
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🔗[DEPENDENT]`

```
1. Symbol Filters (Asset Category + Filter Conditions)
   ↓ AND条件でリアルタイム銘柄リスト更新
2. Symbol Selection (Choose Symbol)
   ↓ 選択と同時に状態表示更新 (st.rerun)
3. Currently Selected Symbol 状態表示
   ↓ Ready to Apply → Active 状態管理
4. Apply Filters 明示的実行
   ↓ 全履歴データ取得 (limit=None)
5. データベース読み込み (ResultsDatabase)
   ↓ 取得済みデータから期間抽出
6. Displaying Period フィルタリング
   ↓ プロット範囲のみ制御
7. 3タブ包括表示 (LPPL Analysis/Convergence/Parameters)
```

#### **重要な設計原則**
- **分離**: Symbol Filters ≠ Data Access ≠ Display Period
- **全データ保証**: Symbol選択後は常に全履歴データアクセス
- **明示制御**: Apply Buttonによる予測可能な動作
- **リアルタイム**: 選択状態の即座フィードバック

### **LPPL計算エンジン** (論文再現保護対象)
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `🎯[CORE]` `🏗️[FOUNDATION]`

**実装メソッド**: `compute_lppl_fit()` + 拡張計算関数群

```python
# 重要な数式実装（変更禁止）
fitted_log_prices = A + B * tau_power_beta + C * tau_power_beta * oscillation
normalized_prices = (prices - price_min) / (price_max - price_min)

# 2025-08-11追加: Future Period計算
extended_lppl_values = calculate_extended_lppl(...)
```

**科学的根拠**: Sornette理論のLPPLモデル + 論文再現テスト100/100スコア維持  
**変更可否**: ❌ **変更厳禁** - 論文再現の根幹、品質保護対象

### **日付変換・時間管理システム** (2025-08-11強化)
**メタ情報**: `🟢[IMPLEMENTED]` `🔧[ENHANCED]` `⭐[HIGH]` `⚙️[FEATURE]` `🔗[DEPENDENT]`

**実装メソッド**: `convert_tc_to_real_date()` + 時間精度対応システム

```python
# tc値を実際の予測日に変換 (時間精度対応)
if tc > 1:
    days_beyond_end = (tc - 1) * total_days
    prediction_date = end_dt + timedelta(days=days_beyond_end)

# 2025-08-11追加: データベース保存時の自動変換
analysis_basis_date = data_period_end  # 分析基準日概念の確立
```

**重要な改善**:
- **データベース一貫性**: tc→datetime変換の自動化
- **分析基準日**: analysis_basis_date概念の完全実装
- **時間精度**: ミリ秒レベルの時間管理対応

**変更可否**: ✅ **変更可能** - アルゴリズム改善可能（科学的正確性維持前提）

---

## 🎨 **UI/UX設計**

### **Symbol Filters Architecture v2 UI設計** (2025-08-11)
**メタ情報**: `🟢[IMPLEMENTED]` `🔥[CRITICAL]` `🔒[STABLE]` `⚙️[FEATURE]` `🎯[CORE]`

#### **5段階UI構造**
1. **Symbol Filters** 🎛️
   - Asset Category (最上段独立セクション)
   - Filter Conditions (プリセット/カスタム選択)
   
2. **Select Symbol** 📈
   - フィルタ結果からのリアルタイム選択
   - 利用可能銘柄の動的更新
   
3. **Currently Selected Symbol** 🎯
   - Ready to Apply / Active / No selection 状態表示
   - 視覚的区別による直感的理解
   
4. **Displaying Period** 📅
   - Symbol選択後に期間範囲設定可能
   - Symbol未選択時は案内表示
   
5. **Apply Filters** 🔄
   - 明示的実行ボタン、Symbol未選択時は無効化
   - "Select Symbol First" 案内表示

### **カラーテーマ・状態表示** (2025-08-11拡張)
**メタ情報**: `🟢[IMPLEMENTED]` `🔧[ENHANCED]` `📋[MEDIUM]` `🔧[UTILITY]` `🎯[ISOLATED]`

#### **従来テーマ**
- **主要色**: 青系（市場データ）、赤系（LPPL予測）
- **アクセント**: 緑系（予測線）

#### **2025-08-11追加: 状態別カラーコード**
- **🔵 Ready to Apply**: Symbol選択済み・未適用状態
- **🟢 Active**: 適用済み・分析表示中状態  
- **ℹ️ Info**: 案内・説明表示
- **⭐ Success**: 操作成功フィードバック
- **❌ Disabled**: 無効化状態表示

**変更可否**: ✅ **変更可能** - ブランディング・アクセシビリティ改善可能

### **レスポンシブ対応**
**メタ情報**: `🟢[IMPLEMENTED]` `📋[MEDIUM]` `🔒[STABLE]` `⚙️[FEATURE]` `🎯[ISOLATED]`

- Streamlit標準の`use_container_width=True`使用
- ワイドレイアウト設定済み

---

## ⚠️ **制限事項と今後の拡張**

### **v1.1での解決済み制限** (2025-08-11)
**メタ情報**: `🟢[RESOLVED]` `⭐[HIGH]` `🔒[STABLE]`

- ✅ **Symbol選択の予測不可能性**: Apply Button制御で完全解決
- ✅ **データアクセス制限**: 全履歴データ保証で解決
- ✅ **期間制御の混乱**: Symbol Filters vs Displaying Period分離で解決
- ✅ **SQL datatype mismatch**: `limit=None`対応で根本解決
- ✅ **リアルタイム状態表示**: Currently Selected Symbolで解決

### **今後の拡張候補**
**メタ情報**: `🔴[TODO]` `📋[MEDIUM]` `🧪[EXPERIMENTAL]` `⚙️[FEATURE]` `🎯[ISOLATED]`

1. **タイムゾーン選択機能**
   - **現状**: UTC固定表示
   - **必要性**: 中程度
   - **実装優先度**: 低

2. **クラスタリング分析拡張**
   - **機能**: 追加の統計手法、リスク管理指標
   - **実装**: より詳細な投資判断支援機能
   - **必要性**: 中程度
   - **実装優先度**: 中

### **v1.1でのパフォーマンス向上** (2025-08-11)
**メタ情報**: `🟢[IMPROVED]` `⭐[HIGH]` `🔒[STABLE]` `🔧[UTILITY]` `🔗[DEPENDENT]`

#### **解決済み問題**
- ✅ **起動時間大幅短縮**: Data Filters最適化で90%短縮実現
- ✅ **SQL クエリ最適化**: インデックス追加で0.0172秒→0.0001秒
- ✅ **メモリ効率**: 不要なファイル生成回避、セッション状態管理改善

#### **現在の制限**
1. **データ取得速度**: API制限に依存（2-5秒、キャッシュ利用で1秒以内）
2. **表示データ量**: Individual Results 5件制限（パフォーマンス考慮）
3. **同時利用**: 複数ユーザーでのAPI制限共有

**変更可否**: ✅ **最適化継続可能** - さらなるキャッシュ・非同期処理改善

### **依存関係リスク**
**メタ情報**: `🟡[PARTIAL]` `⭐[HIGH]` `🔧[EVOLVING]` `🎯[CORE]` `🔗[DEPENDENT]`

1. **外部API**: FRED/Alpha Vantage の可用性に依存
2. **データベース**: SQLite ファイルの整合性に依存
3. **対策**: エラーハンドリング強化済み

---

## 🔄 **メンテナンス指針**

### **変更禁止領域** (2025-08-11強化)
**メタ情報**: `🔒[STABLE]` `🔥[CRITICAL]` `🛡️[PROTECTED]`

1. **LPPL数式実装**: 論文再現100/100スコア保護対象
2. **分析基準日概念**: `analysis_basis_date`基準ソート・表示の絶対遵守
3. **Symbol Filters Architecture**: 完全分離設計の根幹変更禁止
4. **Apply Button制御**: 明示的実行制御の設計思想変更禁止
5. **データベーススキーマ**: UNIQUE制約・インデックス構造の変更禁止

### **改善推奨領域** (2025-08-11更新)
**メタ情報**: `🔧[EVOLVING]` `⚙️[FEATURE]` `📈[ENHANCEMENT]`

1. **🆕 クラスタリング機能**: Prediction Convergence上位互換タブ実装
2. **フィルタ条件拡張**: より多様な検索条件・プリセット追加
3. **可視化改善**: インタラクティブ機能・エクスポート機能
4. **アクセシビリティ**: 国際化・カラーブラインド対応
5. **API統合**: 新データソース追加・フォールバック機能

### **実験可能領域**
**メタ情報**: `🧪[EXPERIMENTAL]` `📝[LOW]`

1. **新しい可視化**: 追加のグラフ種類
2. **インタラクション**: ユーザー操作機能
3. **エクスポート**: CSV/PDF出力機能

---

## 📋 **更新履歴**

| 日付 | 版数 | 更新内容 | 影響度 |
|------|------|----------|--------|
| 2025-08-13 | v1.2 | 🎯 **Tab 4: Crash Prediction Clustering完全実装** - R²重み付きクラスタリング、投資判断支援テーブル、統計的最適化パラメータ、包括的エラーハンドリング | 🔥[CRITICAL] |
| 2025-08-11 | v1.1 | 🎯 **Symbol Filters Architecture v2完全実装** - 銘柄選択・データアクセス・期間制御の完全分離、Apply Button制御、リアルタイム状態表示、SQL最適化 | 🔥[CRITICAL] |
| 2025-08-11 | - | 🔧 多期間収束分析拡張 - 6期間タブ、複数収束判定手法、Multi-Period Analysis、英語統一 | ⭐[HIGH] |
| 2025-08-11 | - | 🛡️ 論文再現保護・品質保証強化 - 100/100スコア維持、エラーハンドリング、パフォーマンス最適化 | ⭐[HIGH] |
| 2025-08-07 | v1.0 | 実装完了版作成、メタ情報導入 | 📋[MEDIUM] |
| 2025-08-06 | - | Parameters タブ改善（フィッティング基準日対応） | 📋[MEDIUM] |
| 2025-08-05 | - | Price & Predictions タブ復旧完了 | 📋[MEDIUM] |

---

## 🏷️ **関連ドキュメント**

- **設計思想**: [implementation_strategy.md](./implementation_strategy.md)
- **メタ情報仕様**: [meta_information_specification.md](./meta_information_specification.md)
- **分析基準日概念**: [CLAUDE.md](../CLAUDE.md#分析基準日-analysis-basis-date-の定義)
- **進捗管理**: [progress_management/CURRENT_PROGRESS.md](./progress_management/CURRENT_PROGRESS.md)
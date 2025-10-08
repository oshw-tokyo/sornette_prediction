# 技術実装詳細計画書
*現在の実装からFCOレベルへのアップグレード実装ガイド*

## 1. 優先実装機能とコード設計

### 1.1 多重時間窓分析システム（最優先）

#### 現在の実装の問題点
```python
# 現在: core/fitting/multi_criteria_selection.py
# 単一の固定期間（通常365日）でのみ分析
result = selector.perform_comprehensive_fitting(data[-365:])
```

#### FCO準拠の新実装
#### FCO準拠実装（✅ `core/fitting/fco_engine.py`実装済み）

多重時間窓分析システムは既に`core/fitting/fco_engine.py`で実装済みです。Boulder Investment Technologiesの`lppls`ライブラリを活用し、以下の機能を提供しています：

- **FCO標準の126時間窓分析**: 125-750日の複数時間窓でのLPPLSフィッティング
- **DS-LPPLS Confidence指標**: 複数窓でのフィッティング成功率ベースの信頼度評価
- **柔軟な窓サイズ設定**: データサイズに応じた最適な時間窓生成
- **品質フィルタリング**: Damping条件（β×ω ≥ 1.0）等のFCO準拠フィルター

**実装ファイル**:
- `core/fitting/fco_engine.py`: 標準FCOエンジン
- `core/fitting/fco_engine_flexible.py`: データサイズ適応型FCOエンジン


### 1.2 DS-LPPLS Trust指標（ブートストラップ法）

```python
# 新規作成: core/fitting/trust_calculator.py

import numpy as np
from scipy import stats
from typing import List, Dict, Tuple
import pandas as pd

class TrustIndicatorCalculator:
    """DS-LPPLS Trust指標の計算（FCO準拠）"""
    
    def __init__(self, n_bootstrap: int = 1000):
        self.n_bootstrap = n_bootstrap
        
    def calculate_trust(self, 
                       prices: pd.Series, 
                       fitted_params: Dict,
                       window_results: pd.DataFrame) -> Dict:
        """ブートストラップ法による信頼性評価"""
        
        bootstrap_results = []
        data_length = len(prices)
        
        for i in range(self.n_bootstrap):
            # リサンプリング（ブロックブートストラップ）
            block_size = int(np.sqrt(data_length))
            n_blocks = data_length // block_size + 1
            
            blocks = []
            for _ in range(n_blocks):
                start_idx = np.random.randint(0, data_length - block_size + 1)
                blocks.append(prices.iloc[start_idx:start_idx + block_size])
            
            resampled = pd.concat(blocks)[:data_length]
            
            # リサンプルデータでフィッティング
            try:
                from core.fitting.fitter import LogarithmPeriodicFitter
                fitter = LogarithmPeriodicFitter()
                t, y = fitter.prepare_data(resampled.values)
                result = fitter.fit_with_multiple_initializations(t, y, n_tries=3)
                
                if result.success:
                    bootstrap_results.append({
                        'tc': result.parameters['tc'],
                        'beta': result.parameters['beta'],
                        'omega': result.parameters['omega'],
                        'r_squared': result.r_squared
                    })
            except:
                continue
        
        if len(bootstrap_results) < self.n_bootstrap * 0.5:
            # ブートストラップの半分以上が失敗した場合
            return {'trust': 0.0, 'confidence_interval': None}
        
        # パラメータの安定性評価
        bootstrap_df = pd.DataFrame(bootstrap_results)
        
        # tc予測の信頼区間
        tc_values = bootstrap_df['tc'].values
        tc_ci = np.percentile(tc_values, [2.5, 97.5])
        tc_std = np.std(tc_values)
        
        # 元の予測との一致度
        original_tc = fitted_params['tc_prediction']['mean']
        tc_consistency = 1.0 - min(1.0, abs(np.mean(tc_values) - original_tc) / tc_std)
        
        # パラメータの変動係数（安定性の指標）
        cv_tc = tc_std / np.mean(tc_values) if np.mean(tc_values) != 0 else 1.0
        cv_beta = bootstrap_df['beta'].std() / bootstrap_df['beta'].mean()
        cv_omega = bootstrap_df['omega'].std() / bootstrap_df['omega'].mean()
        
        # 総合的なTrust指標
        stability_score = 1.0 - np.mean([cv_tc, cv_beta, cv_omega])
        consistency_score = tc_consistency
        convergence_rate = len(bootstrap_results) / self.n_bootstrap
        
        trust_score = np.mean([
            stability_score * 0.4,
            consistency_score * 0.4,
            convergence_rate * 0.2
        ])
        
        return {
            'trust': trust_score,
            'confidence_interval': {
                'tc_lower': tc_ci[0],
                'tc_upper': tc_ci[1],
                'tc_mean': np.mean(tc_values),
                'tc_std': tc_std
            },
            'stability_metrics': {
                'cv_tc': cv_tc,
                'cv_beta': cv_beta,
                'cv_omega': cv_omega
            },
            'bootstrap_success_rate': convergence_rate,
            'n_successful_bootstraps': len(bootstrap_results)
        }
```

### 1.3 レポート生成システム

```python
# 新規作成: applications/reports/pdf_generator.py

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import matplotlib.pyplot as plt
import io
from datetime import datetime
import pandas as pd

class FCOStyleReportGenerator:
    """FCOスタイルのPDFレポート生成"""
    
    def __init__(self, language='ja'):
        self.language = language
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """カスタムスタイルの定義"""
        # タイトルスタイル
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # 日本語対応（必要に応じてフォント設定）
        if self.language == 'ja':
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            # 日本語フォントの登録（システムにインストールされている必要あり）
            # pdfmetrics.registerFont(TTFont('Japanese', '/path/to/japanese/font.ttf'))
    
    def generate_monthly_report(self, 
                               analysis_results: Dict,
                               output_path: str) -> None:
        """月次レポートの生成"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # レポート要素のリスト
        story = []
        
        # 1. タイトルページ
        story.append(Paragraph(
            self._get_title(),
            self.styles['CustomTitle']
        ))
        
        story.append(Spacer(1, 0.2*inch))
        
        # 2. エグゼクティブサマリー
        story.append(Paragraph(
            "エグゼクティブサマリー",
            self.styles['Heading1']
        ))
        
        summary_data = self._create_summary_table(analysis_results)
        story.append(summary_data)
        story.append(PageBreak())
        
        # 3. 市場別分析結果
        for market, data in analysis_results.items():
            story.append(Paragraph(
                f"{market} 分析結果",
                self.styles['Heading1']
            ))
            
            # バブル指標チャート
            chart_buffer = self._create_bubble_chart(data)
            if chart_buffer:
                img = Image(chart_buffer, width=6*inch, height=4*inch)
                story.append(img)
            
            # パラメータテーブル
            param_table = self._create_parameter_table(data)
            story.append(param_table)
            
            story.append(PageBreak())
        
        # PDFビルド
        doc.build(story)
    
    def _get_title(self) -> str:
        """レポートタイトル"""
        current_date = datetime.now()
        if self.language == 'ja':
            return f"LPPL市場クラッシュ予測レポート\\n{current_date.strftime('%Y年%m月')}"
        else:
            return f"LPPL Market Crash Prediction Report\\n{current_date.strftime('%B %Y')}"
    
    def _create_summary_table(self, results: Dict) -> Table:
        """サマリーテーブルの作成"""
        data = [
            ['指標', '値', '評価'],
            ['分析市場数', str(len(results)), ''],
            ['高リスク市場', str(self._count_high_risk(results)), '要注意'],
            ['DS-LPPLS Confidence平均', f"{self._avg_confidence(results):.2%}", ''],
            ['Trust指標平均', f"{self._avg_trust(results):.2%}", ''],
        ]
        
        table = Table(data, colWidths=[2*inch, 2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _create_bubble_chart(self, data: Dict) -> io.BytesIO:
        """バブル指標チャート作成（FCOスタイル）"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # データがある場合のみプロット
            if 'price_history' in data and 'confidence_history' in data:
                # 価格チャート（左軸）
                ax.plot(data['dates'], data['price_history'], 'k-', label='Price')
                ax.set_ylabel('Price', color='k')
                
                # Confidence指標（右軸）
                ax2 = ax.twinx()
                ax2.fill_between(
                    data['dates'],
                    0,
                    data['confidence_history'],
                    where=(data['confidence_history'] > 0),
                    color='green',
                    alpha=0.3,
                    label='Positive Bubble'
                )
                ax2.fill_between(
                    data['dates'],
                    0,
                    data['confidence_history'],
                    where=(data['confidence_history'] < 0),
                    color='red',
                    alpha=0.3,
                    label='Negative Bubble'
                )
                ax2.set_ylabel('DS-LPPLS Confidence (%)', color='g')
                
                # スタイリング
                ax.grid(True, alpha=0.3)
                ax.set_title(f"Bubble Indicators - {data.get('symbol', 'Unknown')}")
                
                # 凡例
                lines1, labels1 = ax.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # BytesIOに保存
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            print(f"Chart creation failed: {e}")
            return None
    
    def _create_parameter_table(self, data: Dict) -> Table:
        """パラメータテーブルの作成"""
        params = data.get('parameters', {})
        
        table_data = [
            ['パラメータ', '値', '信頼区間'],
            ['Critical Time (tc)', 
             f"{params.get('tc_mean', 0):.3f}",
             f"[{params.get('tc_lower', 0):.3f}, {params.get('tc_upper', 0):.3f}]"],
            ['Beta (β)', f"{params.get('beta', 0):.3f}", ''],
            ['Omega (ω)', f"{params.get('omega', 0):.3f}", ''],
            ['R²', f"{params.get('r_squared', 0):.3f}", ''],
            ['Scenario Probability', f"{params.get('scenario_prob', 0):.2%}", ''],
        ]
        
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        return table
    
    def _count_high_risk(self, results: Dict) -> int:
        """高リスク市場のカウント"""
        count = 0
        for market, data in results.items():
            if data.get('tc_prediction', {}).get('mean', 2.0) < 1.3:
                count += 1
        return count
    
    def _avg_confidence(self, results: Dict) -> float:
        """平均Confidence"""
        confidences = [
            data.get('ds_lppls_confidence', 0) 
            for data in results.values()
        ]
        return np.mean(confidences) if confidences else 0.0
    
    def _avg_trust(self, results: Dict) -> float:
        """平均Trust"""
        trusts = [
            data.get('trust', 0) 
            for data in results.values()
        ]
        return np.mean(trusts) if trusts else 0.0
```

## 2. アラート配信システム

### 2.1 LINE Notify統合

```python
# 新規作成: infrastructure/notifications/line_notifier.py

import requests
from typing import Optional, Dict
import json

class LINENotifier:
    """LINE Notify API統合"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_url = "https://notify-api.line.me/api/notify"
        
    def send_alert(self,
                  message: str,
                  image_url: Optional[str] = None,
                  sticker: Optional[Dict] = None) -> bool:
        """LINEアラート送信"""
        
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        data = {'message': message}
        
        # スタンプ追加（オプション）
        if sticker:
            data['stickerPackageId'] = sticker.get('package_id', 1)
            data['stickerId'] = sticker.get('id', 1)
        
        # 画像URL追加（オプション）
        if image_url:
            data['imageThumbnail'] = image_url
            data['imageFullsize'] = image_url
        
        response = requests.post(
            self.api_url,
            headers=headers,
            data=data
        )
        
        return response.status_code == 200
    
    def send_crash_warning(self,
                          symbol: str,
                          tc_days: int,
                          confidence: float,
                          chart_url: Optional[str] = None) -> bool:
        """クラッシュ警告送信"""
        
        message = f"""
⚠️ 【クラッシュ警告】

銘柄: {symbol}
予測クラッシュまで: {tc_days}日
信頼度: {confidence:.1%}

詳細はダッシュボードをご確認ください。
        """.strip()
        
        # 警告スタンプ
        sticker = {
            'package_id': 2,
            'id': 149  # 驚きの顔
        }
        
        return self.send_alert(message, image_url=chart_url, sticker=sticker)
```

## 3. パフォーマンス最適化

### 3.1 分散処理とキャッシング

```python
# 新規作成: infrastructure/optimization/parallel_processor.py

import ray
import redis
import pickle
import hashlib
from typing import Any, Optional, List
import pandas as pd

# Ray初期化（分散処理用）
ray.init(ignore_reinit_error=True)

class OptimizedProcessor:
    """高速化された処理システム"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=False
        )
        
    def _get_cache_key(self, symbol: str, params: Dict) -> str:
        """キャッシュキー生成"""
        param_str = json.dumps(params, sort_keys=True)
        hash_str = hashlib.md5(f"{symbol}:{param_str}".encode()).hexdigest()
        return f"lppl:cache:{hash_str}"
    
    @ray.remote
    def _process_single_symbol(self, symbol: str, data: pd.DataFrame) -> Dict:
        """単一銘柄の並列処理（Ray）"""
        from core.fitting.multi_window_analyzer import MultiWindowLPPLAnalyzer
        
        analyzer = MultiWindowLPPLAnalyzer()
        result = analyzer.analyze_all_windows(data['close'])
        return result
    
    def process_multiple_symbols(self, 
                                symbols: List[str],
                                data_dict: Dict[str, pd.DataFrame]) -> Dict:
        """複数銘柄の並列処理"""
        
        results = {}
        futures = []
        
        for symbol in symbols:
            # キャッシュチェック
            cache_key = self._get_cache_key(symbol, {'type': 'analysis'})
            cached = self.redis_client.get(cache_key)
            
            if cached:
                results[symbol] = pickle.loads(cached)
            else:
                # 並列処理タスク作成
                future = self._process_single_symbol.remote(
                    symbol,
                    data_dict[symbol]
                )
                futures.append((symbol, future))
        
        # 並列処理結果の収集
        for symbol, future in futures:
            result = ray.get(future)
            results[symbol] = result
            
            # キャッシュ保存（1時間）
            cache_key = self._get_cache_key(symbol, {'type': 'analysis'})
            self.redis_client.setex(
                cache_key,
                3600,
                pickle.dumps(result)
            )
        
        return results
```

## 4. API サーバー実装（✅ `fco-api/app/main.py`実装済み）

FastAPIベースのRESTful APIサーバーは既に`fco-api/app/main.py`で実装済みです。以下の機能を提供しています：

- **FCO分析エンドポイント**: 多重時間窓LPPLS分析のREST API
- **データベース統合**: SQLiteベースのFCO分析結果管理
- **Pydanticモデル**: 型安全なデータバリデーション
- **CORS対応**: Reactフロントエンドとの統合

**実装ファイル**:
- `fco-api/app/main.py`: FastAPIアプリケーション
- `fco-api/app/models/`: Pydanticモデル定義
- `fco-api/app/api/v1/endpoints/`: APIエンドポイント


## 5. 統合テストとデプロイメント

### 5.1 統合テスト

```python
# 新規作成: tests/integration/test_fco_compliance.py

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TestFCOCompliance(unittest.TestCase):
    """FCO準拠のテストスイート"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        # テストデータ生成
        dates = pd.date_range(end=datetime.now(), periods=1000, freq='D')
        prices = 100 * np.exp(0.0005 * np.arange(1000) + 0.01 * np.random.randn(1000))
        self.test_data = pd.Series(prices, index=dates, name='close')
        
    def test_multi_window_analysis(self):
        """多重時間窓分析のテスト"""
        from core.fitting.multi_window_analyzer import MultiWindowLPPLAnalyzer
        
        analyzer = MultiWindowLPPLAnalyzer()
        result = analyzer.analyze_all_windows(self.test_data)
        
        # 結果の検証
        self.assertTrue(result['success'])
        self.assertIn('ds_lppls_confidence', result)
        self.assertIn('tc_prediction', result)
        self.assertGreater(result['total_fits'], 0)
        
    def test_trust_indicator(self):
        """Trust指標計算のテスト"""
        from core.fitting.trust_calculator import TrustIndicatorCalculator
        
        calculator = TrustIndicatorCalculator(n_bootstrap=100)
        
        # ダミーパラメータ
        fitted_params = {
            'tc_prediction': {'mean': 1.2, 'std': 0.1}
        }
        window_results = pd.DataFrame({
            'tc': [1.15, 1.20, 1.25],
            'r_squared': [0.8, 0.85, 0.9]
        })
        
        result = calculator.calculate_trust(
            self.test_data,
            fitted_params,
            window_results
        )
        
        self.assertIn('trust', result)
        self.assertIn('confidence_interval', result)
        self.assertGreaterEqual(result['trust'], 0.0)
        self.assertLessEqual(result['trust'], 1.0)
    
    def test_pdf_generation(self):
        """PDFレポート生成のテスト"""
        from applications.reports.pdf_generator import FCOStyleReportGenerator
        
        generator = FCOStyleReportGenerator(language='ja')
        
        # テスト用分析結果
        test_results = {
            'NIKKEI225': {
                'ds_lppls_confidence': 0.75,
                'trust': 0.82,
                'tc_prediction': {'mean': 1.25, 'std': 0.05},
                'parameters': {
                    'tc_mean': 1.25,
                    'tc_lower': 1.20,
                    'tc_upper': 1.30,
                    'beta': 0.35,
                    'omega': 6.5,
                    'r_squared': 0.87,
                    'scenario_prob': 0.68
                }
            }
        }
        
        # PDF生成（一時ファイル）
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            generator.generate_monthly_report(test_results, tmp.name)
            
            # ファイルが作成されたことを確認
            import os
            self.assertTrue(os.path.exists(tmp.name))
            self.assertGreater(os.path.getsize(tmp.name), 0)

if __name__ == '__main__':
    unittest.main()
```

### 5.2 デプロイメントスクリプト

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
      - JPX_API_KEY=${JPX_API_KEY}
      - LINE_ACCESS_TOKEN=${LINE_ACCESS_TOKEN}
    depends_on:
      - redis
      - postgres
    volumes:
      - ./results:/app/results
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: lppl_db
      POSTGRES_USER: lppl_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
```

## まとめ

本技術実装計画により、現在の実装をFCOレベルのサービスにアップグレードする具体的な道筋が明確になりました。

### 優先実装項目（3ヶ月以内）
1. **多重時間窓分析** - FCOの核心機能
2. **DS-LPPLS指標** - 信頼性評価システム
3. **日本市場データ統合** - JPX/Yahoo Finance接続
4. **基本的なAPI** - 商用サービス基盤

### 次期実装項目（6ヶ月以内）
1. **Trust指標** - ブートストラップ法による高度な信頼性評価
2. **PDFレポート生成** - FCOスタイルの月次レポート
3. **LINE/Slack統合** - 日本市場向けアラート
4. **性能最適化** - Ray/Redisによる分散処理

これらの実装により、FCOの科学的精度を維持しつつ、日本・アジア市場に特化した独自のサービスを構築できます。
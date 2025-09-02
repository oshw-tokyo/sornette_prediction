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
```python
# 新規作成: core/fitting/multi_window_analyzer.py

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import itertools

@dataclass
class WindowConfig:
    """時間窓の設定"""
    name: str
    min_days: int
    max_days: int
    step_days: int
    
    def generate_windows(self, data_length: int) -> List[Tuple[int, int]]:
        """指定範囲内の全時間窓を生成"""
        windows = []
        for length in range(self.min_days, min(self.max_days + 1, data_length), self.step_days):
            for start in range(0, data_length - length + 1, self.step_days):
                windows.append((start, start + length))
        return windows

class MultiWindowLPPLAnalyzer:
    """FCO準拠の多重時間窓LPPL分析システム"""
    
    def __init__(self):
        # FCO標準の3スケール時間窓設定
        self.window_configs = [
            WindowConfig("super_short", 100, 200, 10),  # 超短期
            WindowConfig("short", 150, 300, 15),        # 短期
            WindowConfig("long", 500, 1500, 50),        # 長期
        ]
        
        # 既存のフィッターを再利用
        from core.fitting.fitter import LogarithmPeriodicFitter
        self.fitter = LogarithmPeriodicFitter()
        
    def analyze_all_windows(self, 
                           prices: pd.Series,
                           parallel: bool = True) -> Dict:
        """全時間窓での包括的分析"""
        
        all_results = []
        data_length = len(prices)
        
        # 各スケールでの分析
        for config in self.window_configs:
            windows = config.generate_windows(data_length)
            
            if parallel:
                # 並列処理で高速化
                with ProcessPoolExecutor(max_workers=4) as executor:
                    futures = []
                    for start, end in windows:
                        future = executor.submit(
                            self._fit_single_window,
                            prices.iloc[start:end],
                            config.name,
                            (start, end)
                        )
                        futures.append(future)
                    
                    for future in futures:
                        result = future.result()
                        if result is not None:
                            all_results.append(result)
            else:
                # 逐次処理
                for start, end in windows:
                    result = self._fit_single_window(
                        prices.iloc[start:end],
                        config.name,
                        (start, end)
                    )
                    if result is not None:
                        all_results.append(result)
        
        # 結果の統合と評価
        return self._integrate_results(all_results)
    
    def _fit_single_window(self, 
                          window_data: pd.Series,
                          scale_name: str,
                          window_range: Tuple[int, int]) -> Optional[Dict]:
        """単一時間窓でのフィッティング"""
        try:
            # 既存のフィッターを使用
            t, y = self.fitter.prepare_data(window_data.values)
            result = self.fitter.fit_with_multiple_initializations(t, y, n_tries=5)
            
            if result.success and result.r_squared > 0.5:  # 基本的な品質フィルタ
                return {
                    'scale': scale_name,
                    'window': window_range,
                    'tc': result.parameters['tc'],
                    'beta': result.parameters['beta'],
                    'omega': result.parameters['omega'],
                    'r_squared': result.r_squared,
                    'rmse': result.residuals,
                    'window_days': window_range[1] - window_range[0]
                }
        except Exception as e:
            print(f"Fitting failed for window {window_range}: {e}")
        
        return None
    
    def _integrate_results(self, results: List[Dict]) -> Dict:
        """複数時間窓の結果を統合"""
        if not results:
            return {'success': False, 'message': 'No successful fits'}
        
        df = pd.DataFrame(results)
        
        # DS-LPPLS Confidence指標の計算
        confidence_by_scale = {}
        for scale in df['scale'].unique():
            scale_df = df[df['scale'] == scale]
            confidence_by_scale[scale] = len(scale_df) / self._expected_windows(scale)
        
        overall_confidence = np.mean(list(confidence_by_scale.values()))
        
        # k-meansクラスタリングによるtc予測の統合
        from sklearn.cluster import KMeans
        
        tc_values = df['tc'].values.reshape(-1, 1)
        weights = df['r_squared'].values  # R²で重み付け
        
        # 最適クラスタ数の決定（エルボー法の簡易版）
        n_clusters = min(5, len(tc_values) // 10 + 1)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(tc_values, sample_weight=weights)
        
        # 最大クラスタの統計
        cluster_sizes = np.bincount(clusters)
        main_cluster = np.argmax(cluster_sizes)
        main_cluster_mask = clusters == main_cluster
        
        main_tc_values = tc_values[main_cluster_mask].flatten()
        main_weights = weights[main_cluster_mask]
        
        # 重み付き統計
        tc_mean = np.average(main_tc_values, weights=main_weights)
        tc_std = np.sqrt(np.average((main_tc_values - tc_mean)**2, weights=main_weights))
        
        # シナリオ確率（最大クラスタの占有率）
        scenario_probability = len(main_tc_values) / len(tc_values)
        
        return {
            'success': True,
            'total_fits': len(results),
            'ds_lppls_confidence': overall_confidence,
            'confidence_by_scale': confidence_by_scale,
            'tc_prediction': {
                'mean': tc_mean,
                'std': tc_std,
                'scenario_probability': scenario_probability,
                'cluster_size': len(main_tc_values)
            },
            'all_results': df,
            'quality_metrics': {
                'mean_r_squared': df['r_squared'].mean(),
                'median_r_squared': df['r_squared'].median(),
                'successful_scales': len(confidence_by_scale)
            }
        }
    
    def _expected_windows(self, scale: str) -> int:
        """各スケールの期待される窓数（正規化用）"""
        scale_expected = {
            'super_short': 50,
            'short': 40,
            'long': 20
        }
        return scale_expected.get(scale, 30)
```

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

## 2. 日本市場データ統合

### 2.1 JPXデータフィード接続

```python
# 新規作成: infrastructure/data_sources/jpx_client.py

import requests
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import json

class JPXDataClient:
    """日本取引所グループ（JPX）データクライアント"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.jpx.co.jp/v1"
        self.session = requests.Session()
        self._authenticate()
        
    def _authenticate(self):
        """認証処理"""
        # JPX APIの認証実装（仕様に基づく）
        pass
    
    def get_nikkei225_components(self) -> List[str]:
        """日経225構成銘柄取得"""
        endpoint = f"{self.base_url}/indices/nikkei225/components"
        response = self.session.get(endpoint)
        
        if response.status_code == 200:
            return response.json()['components']
        else:
            raise Exception(f"Failed to get Nikkei 225 components: {response.status_code}")
    
    def get_historical_data(self,
                          symbol: str,
                          start_date: datetime,
                          end_date: datetime,
                          interval: str = 'daily') -> pd.DataFrame:
        """過去データ取得"""
        
        endpoint = f"{self.base_url}/prices/historical"
        params = {
            'symbol': symbol,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'interval': interval
        }
        
        response = self.session.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['prices'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            return df
        else:
            raise Exception(f"Failed to get historical data: {response.status_code}")
    
    def get_realtime_price(self, symbol: str) -> Dict:
        """リアルタイム価格取得"""
        endpoint = f"{self.base_url}/prices/realtime/{symbol}"
        response = self.session.get(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    def get_market_statistics(self) -> Dict:
        """市場統計情報"""
        endpoint = f"{self.base_url}/market/statistics"
        response = self.session.get(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
```

### 2.2 Yahoo Finance Japan統合（バックアップ）

```python
# 新規作成: infrastructure/data_sources/yahoo_japan_client.py

import yfinance as yf
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

class YahooJapanClient:
    """Yahoo Finance Japan データクライアント（バックアップ用）"""
    
    def __init__(self):
        # Yahoo Finance は.T サフィックスで東証銘柄にアクセス
        self.suffix = '.T'
        
    def get_stock_data(self,
                      code: str,
                      start_date: datetime,
                      end_date: datetime) -> Optional[pd.DataFrame]:
        """株価データ取得"""
        
        # 銘柄コードに東証サフィックス追加
        ticker = f"{code}{self.suffix}"
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)
            
            if not df.empty:
                # カラム名を統一
                df = df.rename(columns={
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                return df
            
        except Exception as e:
            print(f"Failed to fetch data for {ticker}: {e}")
            
        return None
    
    def get_index_data(self, index_code: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """指数データ取得"""
        
        index_mapping = {
            'N225': '^N225',      # 日経225
            'TOPIX': '^TOPX',     # TOPIX
            'MOTHERS': '^MTHR',   # マザーズ
        }
        
        ticker = index_mapping.get(index_code, index_code)
        
        try:
            index = yf.Ticker(ticker)
            df = index.history(period=period)
            return df
            
        except Exception as e:
            print(f"Failed to fetch index data for {ticker}: {e}")
            
        return None
```

## 3. アラート配信システム

### 3.1 LINE Notify統合

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

## 4. パフォーマンス最適化

### 4.1 分散処理とキャッシング

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

## 5. API サーバー実装

```python
# 新規作成: applications/api/main.py

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict
import jwt
from datetime import datetime, timedelta

app = FastAPI(title="LPPL Prediction API", version="1.0.0")
security = HTTPBearer()

class PredictionRequest(BaseModel):
    symbol: str
    period_days: Optional[int] = 365
    confidence_threshold: Optional[float] = 0.5

class PredictionResponse(BaseModel):
    symbol: str
    tc_prediction: float
    tc_days: int
    confidence: float
    trust: float
    risk_level: str
    analysis_date: datetime

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
    
    def verify_jwt(self, jwtoken: str) -> bool:
        try:
            payload = jwt.decode(jwtoken, SECRET_KEY, algorithms=["HS256"])
            return True
        except:
            return False

@app.post("/api/v1/predict", response_model=PredictionResponse)
async def predict_crash(
    request: PredictionRequest,
    token: str = Depends(JWTBearer())
):
    """単一銘柄のクラッシュ予測"""
    
    try:
        # データ取得
        from infrastructure.data_sources.unified_data_client import UnifiedDataClient
        client = UnifiedDataClient()
        data = client.get_historical_data(
            request.symbol,
            period_days=request.period_days
        )
        
        # 分析実行
        from core.fitting.multi_window_analyzer import MultiWindowLPPLAnalyzer
        from core.fitting.trust_calculator import TrustIndicatorCalculator
        
        analyzer = MultiWindowLPPLAnalyzer()
        trust_calc = TrustIndicatorCalculator()
        
        # 多重時間窓分析
        result = analyzer.analyze_all_windows(data['close'])
        
        # Trust指標計算
        trust_result = trust_calc.calculate_trust(
            data['close'],
            result,
            result['all_results']
        )
        
        # リスクレベル判定
        tc_mean = result['tc_prediction']['mean']
        if tc_mean < 1.1:
            risk_level = "CRITICAL"
        elif tc_mean < 1.3:
            risk_level = "HIGH"
        elif tc_mean < 1.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # tc を日数に変換
        current_t = 1.0  # 現在時点
        tc_days = int((tc_mean - current_t) * request.period_days)
        
        return PredictionResponse(
            symbol=request.symbol,
            tc_prediction=tc_mean,
            tc_days=tc_days,
            confidence=result['ds_lppls_confidence'],
            trust=trust_result['trust'],
            risk_level=risk_level,
            analysis_date=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/markets/japan")
async def get_japan_markets(token: str = Depends(JWTBearer())):
    """日本市場の銘柄リスト"""
    
    markets = {
        "indices": ["N225", "TOPIX", "MOTHERS", "JPX400"],
        "major_stocks": [
            "7203",  # トヨタ
            "6758",  # ソニー
            "9984",  # ソフトバンクグループ
            "6861",  # キーエンス
            "8306",  # 三菱UFJ
        ],
        "sectors": [
            "automobiles",
            "technology",
            "finance",
            "retail",
            "pharmaceuticals"
        ]
    }
    
    return markets

@app.post("/api/v1/batch-analysis")
async def batch_analysis(
    symbols: List[str],
    token: str = Depends(JWTBearer())
):
    """複数銘柄の一括分析"""
    
    from infrastructure.optimization.parallel_processor import OptimizedProcessor
    
    processor = OptimizedProcessor()
    
    # データ取得
    data_dict = {}
    for symbol in symbols:
        # データ取得処理
        pass
    
    # 並列処理
    results = processor.process_multiple_symbols(symbols, data_dict)
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 6. 統合テストとデプロイメント

### 6.1 統合テスト

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

### 6.2 デプロイメントスクリプト

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
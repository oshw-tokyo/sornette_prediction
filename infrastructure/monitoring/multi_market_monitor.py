#!/usr/bin/env python3
"""
マルチマーケット・マルチタイムフレーム監視システム

複数市場を様々な期間で継続的に分析し、
tc値の時系列変化とメタ情報を統合管理
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

class MarketIndex(Enum):
    """監視対象市場インデックス"""
    NASDAQ = "NASDAQCOM"
    SP500 = "SP500"
    DJIA = "DJIA"
    RUSSELL2000 = "RUT"
    NIKKEI = "NIKKEI225"
    DAX = "DEXDAXS"
    FTSE = "FTSE100"
    CRYPTO_BTC = "BTCUSD"
    GOLD = "GOLDAMGBD228NLBM"

class TimeWindow(Enum):
    """分析期間ウィンドウ"""
    SHORT = 365      # 1年
    MEDIUM = 730     # 2年
    LONG = 1095      # 3年
    EXTENDED = 1825  # 5年

class TCInterpretation(Enum):
    """tc値の解釈カテゴリ"""
    IMMINENT = "imminent_risk"          # tc ∈ [1.0, 1.1]
    ACTIONABLE = "actionable"           # tc ∈ [1.1, 1.3]
    MONITORING = "monitoring_required"   # tc ∈ [1.3, 1.5]
    EXTENDED = "extended_horizon"        # tc ∈ [1.5, 2.0]
    LONG_TERM = "long_term_trend"       # tc ∈ [2.0, 3.0]
    INFORMATIONAL = "informational_only" # tc > 3.0

@dataclass
class FittingResult:
    """個別フィッティング結果"""
    market: MarketIndex
    window_days: int
    start_date: datetime
    end_date: datetime
    tc: float
    beta: float
    omega: float
    r_squared: float
    rmse: float
    predicted_date: datetime
    tc_interpretation: TCInterpretation
    confidence_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'market': self.market.value,
            'window_days': self.window_days,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'tc': self.tc,
            'beta': self.beta,
            'omega': self.omega,
            'r_squared': self.r_squared,
            'rmse': self.rmse,
            'predicted_date': self.predicted_date.isoformat(),
            'tc_interpretation': self.tc_interpretation.value,
            'confidence_score': self.confidence_score,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class MarketSnapshot:
    """特定時点での全市場スナップショット"""
    snapshot_date: datetime
    results: List[FittingResult]
    
    def get_high_risk_markets(self, tc_threshold: float = 1.3) -> List[FittingResult]:
        """高リスク市場の抽出"""
        return [r for r in self.results 
                if r.tc <= tc_threshold and r.r_squared > 0.7]
    
    def get_market_summary(self) -> Dict[str, Any]:
        """市場サマリーの生成"""
        return {
            'total_markets': len(self.results),
            'high_risk_count': len(self.get_high_risk_markets()),
            'average_tc': np.mean([r.tc for r in self.results]),
            'average_r2': np.mean([r.r_squared for r in self.results]),
            'risk_distribution': self._get_risk_distribution()
        }
    
    def _get_risk_distribution(self) -> Dict[str, int]:
        """リスクレベル分布"""
        distribution = {}
        for interpretation in TCInterpretation:
            count = sum(1 for r in self.results 
                       if r.tc_interpretation == interpretation)
            distribution[interpretation.value] = count
        return distribution

class MultiMarketMonitor:
    """マルチマーケット監視システム"""
    
    def __init__(self, markets: List[MarketIndex] = None, 
                 windows: List[TimeWindow] = None):
        """
        Args:
            markets: 監視対象市場リスト
            windows: 分析期間ウィンドウリスト
        """
        self.markets = markets or list(MarketIndex)
        self.windows = windows or list(TimeWindow)
        self.history = []  # 全履歴保存
        self.latest_snapshot = None
        
        # パラメータマネージャーとデータクライアントの初期化
        from src.parameter_management import AdaptiveParameterManager
        from src.data_sources.fred_data_client import FREDDataClient
        
        self.param_manager = AdaptiveParameterManager()
        self.data_client = FREDDataClient()
    
    def analyze_market_window(self, market: MarketIndex, 
                            window: TimeWindow, 
                            end_date: datetime = None) -> Optional[FittingResult]:
        """単一市場・単一期間の分析"""
        
        if end_date is None:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=window.value)
        
        try:
            # データ取得
            data = self.data_client.get_series_data(
                market.value, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if data is None or len(data) < 100:  # 最低100日必要
                return None
            
            # LPPLフィッティング実行（簡略版）
            fitting_result = self._perform_lppl_fitting(data)
            
            if fitting_result is None:
                return None
            
            # tc値の解釈
            tc = fitting_result['tc']
            tc_interpretation = self._interpret_tc(tc)
            
            # 予測日計算
            observation_days = (data.index[-1] - data.index[0]).days
            days_to_critical = (tc - 1.0) * observation_days
            predicted_date = data.index[-1] + timedelta(days=days_to_critical)
            
            # 信頼度スコア計算
            confidence_score = self._calculate_confidence(
                fitting_result, tc_interpretation
            )
            
            result = FittingResult(
                market=market,
                window_days=window.value,
                start_date=data.index[0],
                end_date=data.index[-1],
                tc=tc,
                beta=fitting_result['beta'],
                omega=fitting_result['omega'],
                r_squared=fitting_result['r_squared'],
                rmse=fitting_result['rmse'],
                predicted_date=predicted_date,
                tc_interpretation=tc_interpretation,
                confidence_score=confidence_score
            )
            
            # 多基準選択結果がある場合は保存
            if 'selection_result' in fitting_result:
                try:
                    from src.data_management.prediction_database import PredictionDatabase
                    db = PredictionDatabase()
                    session_id = db.save_multi_criteria_results(
                        fitting_result['selection_result'],
                        market.value,
                        window.value,
                        data.index[0],
                        data.index[-1]
                    )
                    print(f"  📊 多基準結果保存: セッションID {session_id[:8]}...")
                except Exception as e:
                    print(f"  ⚠️ 多基準結果保存失敗: {str(e)}")
            
            return result
            
        except Exception as e:
            print(f"エラー: {market.value}/{window.value}日 - {str(e)}")
            return None
    
    def _perform_lppl_fitting(self, data: pd.DataFrame, use_multi_criteria: bool = True) -> Optional[Dict]:
        """LPPLフィッティングの実行（多基準選択対応）"""
        
        if use_multi_criteria:
            # 多基準選択システムを使用
            from src.fitting.multi_criteria_selection import MultiCriteriaSelector
            
            selector = MultiCriteriaSelector()
            selection_result = selector.perform_comprehensive_fitting(data)
            
            if selection_result.selections:
                # デフォルト選択結果を返す（R²最大化）
                default_candidate = selection_result.get_selected_result()
                if default_candidate:
                    return {
                        'tc': default_candidate.tc,
                        'beta': default_candidate.beta,
                        'omega': default_candidate.omega,
                        'r_squared': default_candidate.r_squared,
                        'rmse': default_candidate.rmse,
                        'selection_result': selection_result  # 完全な選択結果も保持
                    }
        
        # フォールバック：従来の簡易フィッティング
        from src.fitting.utils import logarithm_periodic_func
        from scipy.optimize import curve_fit
        
        log_prices = np.log(data['Close'].values)
        t = np.linspace(0, 1, len(data))
        
        best_result = None
        best_r2 = 0
        
        # 簡易的な初期値セット
        for tc_init in [1.1, 1.2, 1.3, 1.5, 2.0]:
            try:
                p0 = [tc_init, 0.35, 6.5, 0.0, 
                      np.mean(log_prices), 
                      (log_prices[-1] - log_prices[0]) / len(log_prices),
                      0.1]
                
                bounds = (
                    [1.01, 0.1, 3.0, -np.pi, -10, -10, -1.0],
                    [3.0, 0.8, 15.0, np.pi, 10, 10, 1.0]
                )
                
                popt, _ = curve_fit(
                    logarithm_periodic_func, t, log_prices,
                    p0=p0, bounds=bounds, method='trf',
                    maxfev=3000
                )
                
                y_pred = logarithm_periodic_func(t, *popt)
                r_squared = 1 - (np.sum((log_prices - y_pred)**2) / 
                               np.sum((log_prices - np.mean(log_prices))**2))
                
                if r_squared > best_r2:
                    best_r2 = r_squared
                    best_result = {
                        'tc': popt[0],
                        'beta': popt[1],
                        'omega': popt[2],
                        'r_squared': r_squared,
                        'rmse': np.sqrt(np.mean((log_prices - y_pred)**2))
                    }
                    
            except:
                continue
        
        return best_result
    
    def _interpret_tc(self, tc: float) -> TCInterpretation:
        """tc値の解釈"""
        if tc < 1.0:
            return TCInterpretation.INFORMATIONAL  # 無効
        elif tc <= 1.1:
            return TCInterpretation.IMMINENT
        elif tc <= 1.3:
            return TCInterpretation.ACTIONABLE
        elif tc <= 1.5:
            return TCInterpretation.MONITORING
        elif tc <= 2.0:
            return TCInterpretation.EXTENDED
        elif tc <= 3.0:
            return TCInterpretation.LONG_TERM
        else:
            return TCInterpretation.INFORMATIONAL
    
    def _calculate_confidence(self, fitting_result: Dict, 
                            tc_interpretation: TCInterpretation) -> float:
        """信頼度スコアの計算"""
        
        base_score = fitting_result['r_squared']
        
        # tc値による調整
        tc_multipliers = {
            TCInterpretation.IMMINENT: 1.0,
            TCInterpretation.ACTIONABLE: 0.9,
            TCInterpretation.MONITORING: 0.7,
            TCInterpretation.EXTENDED: 0.5,
            TCInterpretation.LONG_TERM: 0.3,
            TCInterpretation.INFORMATIONAL: 0.1
        }
        
        multiplier = tc_multipliers.get(tc_interpretation, 0.5)
        
        # 理論値との適合性
        beta_score = 1.0 - abs(fitting_result['beta'] - 0.33) / 0.33
        omega_score = 1.0 - abs(fitting_result['omega'] - 6.36) / 6.36
        
        theory_score = (beta_score + omega_score) / 2
        theory_score = max(0, min(1, theory_score))
        
        # 総合スコア
        confidence = base_score * multiplier * (0.7 + 0.3 * theory_score)
        
        return min(1.0, confidence)
    
    def run_full_analysis(self, end_date: datetime = None, 
                         parallel: bool = True) -> MarketSnapshot:
        """全市場・全期間の分析実行"""
        
        if end_date is None:
            end_date = datetime.now()
        
        print(f"🎯 マルチマーケット分析開始: {end_date.date()}")
        print(f"   市場数: {len(self.markets)}")
        print(f"   期間数: {len(self.windows)}")
        print(f"   総分析数: {len(self.markets) * len(self.windows)}")
        
        results = []
        
        if parallel:
            # 並列実行
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                
                for market in self.markets:
                    for window in self.windows:
                        future = executor.submit(
                            self.analyze_market_window, 
                            market, window, end_date
                        )
                        futures.append((future, market, window))
                
                for future, market, window in futures:
                    try:
                        result = future.result(timeout=60)
                        if result:
                            results.append(result)
                            print(f"✅ {market.value}/{window.value}日: tc={result.tc:.3f}")
                    except Exception as e:
                        print(f"❌ {market.value}/{window.value}日: エラー")
        else:
            # 逐次実行
            for market in self.markets:
                for window in self.windows:
                    result = self.analyze_market_window(market, window, end_date)
                    if result:
                        results.append(result)
        
        # スナップショット作成
        snapshot = MarketSnapshot(
            snapshot_date=end_date,
            results=results
        )
        
        self.latest_snapshot = snapshot
        self.history.append(snapshot)
        
        print(f"\n📊 分析完了: {len(results)}件の有効結果")
        
        return snapshot
    
    def analyze_tc_trends(self, market: MarketIndex, 
                         window: TimeWindow) -> Dict[str, Any]:
        """特定市場・期間のtc値時系列トレンド分析"""
        
        # 該当する履歴を抽出
        market_history = []
        for snapshot in self.history:
            for result in snapshot.results:
                if (result.market == market and 
                    result.window_days == window.value):
                    market_history.append({
                        'date': snapshot.snapshot_date,
                        'tc': result.tc,
                        'r_squared': result.r_squared,
                        'predicted_date': result.predicted_date
                    })
        
        if len(market_history) < 2:
            return {'trend': 'insufficient_data'}
        
        # 時系列でソート
        market_history.sort(key=lambda x: x['date'])
        
        # トレンド分析
        tc_values = [h['tc'] for h in market_history]
        tc_trend = np.polyfit(range(len(tc_values)), tc_values, 1)[0]
        
        # 解釈
        if tc_trend < -0.1:
            trend_interpretation = "approaching_critical"  # 臨界点接近中
        elif tc_trend > 0.1:
            trend_interpretation = "moving_away"  # 臨界点から遠ざかる
        else:
            trend_interpretation = "stable"  # 安定
        
        return {
            'market': market.value,
            'window': window.value,
            'history': market_history,
            'tc_trend': tc_trend,
            'interpretation': trend_interpretation,
            'latest_tc': tc_values[-1],
            'tc_change': tc_values[-1] - tc_values[0] if len(tc_values) > 1 else 0
        }
    
    def generate_risk_dashboard(self) -> Dict[str, Any]:
        """リスクダッシュボード生成"""
        
        if not self.latest_snapshot:
            return {'status': 'no_data'}
        
        snapshot = self.latest_snapshot
        high_risk_markets = snapshot.get_high_risk_markets()
        
        # リスクレベル別に分類
        risk_levels = {
            'imminent': [],
            'actionable': [],
            'monitoring': [],
            'long_term': []
        }
        
        for result in snapshot.results:
            if result.confidence_score > 0.5:  # 信頼度閾値
                if result.tc_interpretation == TCInterpretation.IMMINENT:
                    risk_levels['imminent'].append(result)
                elif result.tc_interpretation == TCInterpretation.ACTIONABLE:
                    risk_levels['actionable'].append(result)
                elif result.tc_interpretation == TCInterpretation.MONITORING:
                    risk_levels['monitoring'].append(result)
                elif result.tc_interpretation in [TCInterpretation.LONG_TERM, 
                                                TCInterpretation.EXTENDED]:
                    risk_levels['long_term'].append(result)
        
        # 各リスクレベルをスコア順にソート
        for level in risk_levels:
            risk_levels[level].sort(key=lambda x: x.confidence_score, reverse=True)
        
        return {
            'snapshot_date': snapshot.snapshot_date.isoformat(),
            'summary': snapshot.get_market_summary(),
            'risk_levels': {
                level: [r.to_dict() for r in results]
                for level, results in risk_levels.items()
            },
            'top_risks': [r.to_dict() for r in high_risk_markets[:5]],
            'recommendations': self._generate_recommendations(risk_levels)
        }
    
    def _generate_recommendations(self, risk_levels: Dict) -> List[str]:
        """リスクレベルに基づく推奨事項生成"""
        
        recommendations = []
        
        if risk_levels['imminent']:
            recommendations.append(
                f"🚨 {len(risk_levels['imminent'])}市場で差し迫ったリスク検出 - 即座の対応推奨"
            )
        
        if risk_levels['actionable']:
            recommendations.append(
                f"⚠️ {len(risk_levels['actionable'])}市場でアクション可能なシグナル - リスク管理計画策定"
            )
        
        if risk_levels['monitoring']:
            recommendations.append(
                f"👁️ {len(risk_levels['monitoring'])}市場で監視継続推奨 - 週次レビュー"
            )
        
        if len(risk_levels['long_term']) > 5:
            recommendations.append(
                f"📊 長期的な過熱傾向が広範囲で観測 - マクロ環境の再評価推奨"
            )
        
        return recommendations
    
    def export_results(self, filepath: str = None):
        """結果のエクスポート"""
        
        if filepath is None:
            os.makedirs('results/multi_market_monitoring', exist_ok=True)
            filepath = f'results/multi_market_monitoring/snapshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        dashboard = self.generate_risk_dashboard()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)
        
        print(f"📄 結果エクスポート: {filepath}")
    
    def run_continuous_monitoring(self, interval_days: int = 7, 
                                duration_days: int = 30):
        """継続的モニタリングのシミュレーション"""
        
        print(f"🔄 継続モニタリング開始")
        print(f"   間隔: {interval_days}日")
        print(f"   期間: {duration_days}日")
        
        end_date = datetime.now()
        
        for i in range(0, duration_days, interval_days):
            current_date = end_date - timedelta(days=duration_days - i)
            print(f"\n--- {current_date.date()} 分析 ---")
            
            snapshot = self.run_full_analysis(current_date, parallel=False)
            
            # 高リスク市場の表示
            high_risk = snapshot.get_high_risk_markets()
            if high_risk:
                print(f"⚠️ 高リスク市場検出:")
                for r in high_risk[:3]:
                    print(f"   {r.market.value}: tc={r.tc:.3f}, 予測日={r.predicted_date.date()}")
        
        # トレンド分析
        print(f"\n📈 トレンド分析結果:")
        for market in [MarketIndex.NASDAQ, MarketIndex.SP500]:
            for window in [TimeWindow.MEDIUM, TimeWindow.LONG]:
                trend = self.analyze_tc_trends(market, window)
                if trend.get('interpretation'):
                    print(f"   {market.value}/{window.value}日: {trend['interpretation']}")
                    print(f"     tc変化: {trend.get('tc_change', 0):.3f}")

# 使用例
def example_usage():
    """使用例の実演"""
    
    # 主要市場のみで高速デモ
    monitor = MultiMarketMonitor(
        markets=[MarketIndex.NASDAQ, MarketIndex.SP500],
        windows=[TimeWindow.SHORT, TimeWindow.MEDIUM]
    )
    
    # 単一時点分析
    snapshot = monitor.run_full_analysis(parallel=False)
    
    # リスクダッシュボード生成
    dashboard = monitor.generate_risk_dashboard()
    
    print(f"\n🎯 リスクダッシュボード:")
    print(f"   分析市場数: {dashboard['summary']['total_markets']}")
    print(f"   高リスク市場: {dashboard['summary']['high_risk_count']}")
    print(f"   平均tc: {dashboard['summary']['average_tc']:.3f}")
    
    if dashboard['top_risks']:
        print(f"\n⚠️ トップリスク:")
        for risk in dashboard['top_risks'][:3]:
            print(f"   {risk['market']}: tc={risk['tc']:.3f}, 信頼度={risk['confidence_score']:.2f}")
    
    # 結果エクスポート
    monitor.export_results()

if __name__ == "__main__":
    example_usage()
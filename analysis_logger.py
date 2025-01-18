import json
import pandas as pd
import os
from datetime import datetime, timedelta 



class AnalysisLogger:
    def __init__(self, base_dir='analysis_results'):
        self.base_dir = base_dir
        self.ensure_directories()
        
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        directories = ['summaries', 'plots', 'metrics', 'raw_data']
        for dir_name in [os.path.join(self.base_dir, d) for d in directories]:
            os.makedirs(dir_name, exist_ok=True)

    def generate_analysis_id(self, symbol):
        """分析IDを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{symbol}_{timestamp}"
    
    def save_analysis_results(self, symbol, results, data, quality_metrics, stability_metrics, 
                            start_date, end_date, plots_info):
        analysis_id = self.generate_analysis_id(symbol)
        
        tc, m, omega, phi, A, B, C = results
        current_time = len(data)
        days_to_tc = tc - current_time
        
        # 安定性分析による予測範囲を計算
        tc_mean, tc_std, tc_cv, window_consistency = stability_metrics
        if tc_mean is not None:
            mean_days_from_end = tc_mean - current_time
            predicted_mean_date = end_date + pd.Timedelta(days=int(mean_days_from_end))
            stability_range = {
                'start': (predicted_mean_date - pd.Timedelta(days=int(tc_std))).strftime('%Y年%m月%d日'),
                'end': (predicted_mean_date + pd.Timedelta(days=int(tc_std))).strftime('%Y年%m月%d日')
            }
        else:
            stability_range = {'start': None, 'end': None}

        # フィット品質の評価
        fit_metrics = self._evaluate_fit_quality(
            quality_metrics['R2'],
            quality_metrics['RMSE'],
            quality_metrics['Residuals_normality_p']
        )

        # 安定性の評価
        stability_metrics_dict = self._evaluate_stability(
            tc_cv,  # tc_cv
            tc_std,  # tc_std
            window_consistency
        )

        # CSVデータの作成
        csv_data = {
            'analysis_id': analysis_id,
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'days_to_tc': round(days_to_tc, 2),
            'predicted_date': (end_date + pd.Timedelta(days=int(days_to_tc))).strftime('%Y-%m-%d'),
            'r2': round(quality_metrics['R2'], 3),
            'rmse': round(quality_metrics['RMSE'], 3),
            'residuals_normality': round(quality_metrics['Residuals_normality_p'], 3),
            'max_autocorr': round(quality_metrics['Max_autocorr'], 3),
            'tc_cv': round(tc_cv, 3) if tc_cv is not None else None,
            'tc_std': round(tc_std, 3) if tc_std is not None else None,
            'window_consistency': round(window_consistency, 3),
            'm': round(m, 3),
            'omega': round(omega, 3),
            'phi': round(phi, 3)
        }

        # CSVファイルに保存
        csv_path = os.path.join(self.base_dir, 'metrics', 'analysis_records.csv')
        df_new = pd.DataFrame([csv_data])
        if os.path.exists(csv_path):
            df_new.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            df_new.to_csv(csv_path, index=False)

        # JSON形式の詳細データも保存
        summary_path = os.path.join(self.base_dir, 'summaries', f'{analysis_id}_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis_id': analysis_id,
                'symbol': symbol,
                'analysis_date': csv_data['analysis_date'],
                'period': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                },
                'critical_point': {
                    'days_to_tc': float(days_to_tc),
                    'predicted_date': csv_data['predicted_date'],
                    'parameters': {
                        'tc': float(tc),
                        'm': float(m),
                        'omega': float(omega),
                        'phi': float(phi),
                        'A': float(A),
                        'B': float(B),
                        'C': float(C)
                    }
                },
                'quality_metrics': fit_metrics,
                'stability_metrics': stability_metrics_dict,
                'plots': plots_info,
                'stability_range': stability_range
            }, f, indent=2, ensure_ascii=False)
        
        return analysis_id
    
    def generate_report(self, analysis_id):
        """分析レポートを生成（予測手法の比較を含む）"""
        summary_path = os.path.join(self.base_dir, 'summaries', f'{analysis_id}_summary.json')
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # フィット品質と安定性の評価を計算
        fit_quality, fit_quality_num = self._evaluate_fit_quality(
            summary['quality_metrics']['R2'],
            summary['quality_metrics']['RMSE'],
            summary['quality_metrics']['normality_p_value']
        )
        
        window_consistency = self._calculate_window_consistency(
            (summary['stability_metrics']['tc_mean'],
            summary['stability_metrics']['tc_std'],
            summary['stability_metrics']['tc_cv'])
        )
        
        stability, stability_num = self._evaluate_stability(
            summary['stability_metrics']['tc_cv'],
            summary['stability_metrics']['tc_std'],
            window_consistency
        )
        
        report = f"""
=== 対数周期性解析レポート ===
分析ID: {summary['analysis_id']}
銘柄: {summary['symbol']}
分析日時: {summary['analysis_date']}

【フィット品質指標】
- 決定係数(R²): {summary['quality_metrics']['R2']:.3f}
- 平均二乗誤差(RMSE): {summary['quality_metrics']['RMSE']:.3f}
- 残差正規性(p値): {summary['quality_metrics']['normality_p_value']:.3f}
- 最大自己相関: {summary['quality_metrics']['max_autocorr']:.3f}

【安定性指標】
- 変動係数(CV): {summary['stability_metrics']['tc_cv']:.3f}
- 標準偏差: {summary['stability_metrics']['tc_std']:.1f}日
- 時間窓一貫性: {window_consistency:.3f}

【予測結果】
- 臨界時点までの日数: {summary['critical_point']['days_to_tc']:.1f}日
- 予測日: {summary['critical_point']['predicted_date']}
- 予測範囲: {summary['stability_range']['start']} ～ {summary['stability_range']['end']}

【モデルパラメータ】
- べき指数(m): {summary['critical_point']['parameters']['m']:.3f}
- 角振動数(ω): {summary['critical_point']['parameters']['omega']:.3f}
- 位相(φ): {summary['critical_point']['parameters']['phi']:.3f}

分析グラフは {os.path.join(self.base_dir, 'plots')} に保存されています。
"""
        return report

    def _generate_evaluation(self, summary, fit_quality, fit_quality_num, stability, stability_num):
        """結果の評価コメントを生成"""
        evaluation = []
        
        # フィット品質の評価
        if fit_quality == "very_high":
            evaluation.append("✓ モデルフィットの品質が非常に高く、信頼性の高い予測が期待できます")
        elif fit_quality == "high":
            evaluation.append("✓ モデルフィットの品質が良好です")
        elif fit_quality == "low":
            evaluation.append("⚠ モデルフィットの品質が低く、予測の信頼性に注意が必要です")
        else:  # very_low
            evaluation.append("⚠ モデルフィットの品質が非常に低く、予測結果の使用は推奨されません")
        
        # 安定性の評価
        if stability == "very_high":
            evaluation.append("✓ 予測が非常に安定しており、高い再現性が期待できます")
        elif stability == "high":
            evaluation.append("✓ 予測の安定性が良好です")
        elif stability == "low":
            evaluation.append("⚠ 予測の安定性が低く、結果が変動する可能性があります")
        else:  # very_low
            evaluation.append("⚠ 予測が非常に不安定です")
        
        # 臨界時点までの期間による評価
        days_to_tc = summary['critical_point']['days_to_tc']
        if days_to_tc <= 30:
            evaluation.append(f"注目: 臨界時点まで30日以内 ({days_to_tc:.1f}日)")
        elif days_to_tc <= 60:
            evaluation.append(f"注目: 臨界時点まで60日以内 ({days_to_tc:.1f}日)")
        
        # 予測手法間の一貫性評価
        if summary['stability_metrics']['tc_cv'] is not None:
            cv = summary['stability_metrics']['tc_cv']
            if cv < 0.1:
                evaluation.append("✓ 異なる予測手法間で高い一貫性が確認されています")
            elif cv < 0.3:
                evaluation.append("△ 予測手法間で一定の一貫性が見られます")
            else:
                evaluation.append("⚠ 予測手法間で一貫性が低く、結果の解釈に注意が必要です")
        
        return "\n".join(evaluation)
    
    # 警告評価のためのヘルパーメソッド
    def _evaluate_fit_quality(self, r2, rmse, residuals_norm_p):
        """フィットの品質指標を返す
        
        Parameters:
        -----------
        r2: float
            決定係数 (0 to 1)
        rmse: float
            平均二乗誤差の平方根
        residuals_norm_p: float
            残差の正規性検定のp値
        
        Returns:
        --------
        dict:
            各品質指標値
        """
        return {
            'r2': r2,
            'rmse': rmse,
            'residuals_normality': residuals_norm_p
        }

    def _evaluate_stability(self, tc_cv, tc_std, window_consistency):
        """安定性指標を返す
        
        Parameters:
        -----------
        tc_cv: float
            臨界時点の変動係数
        tc_std: float
            臨界時点の標準偏差（日数）
        window_consistency: float
            異なる時間窓での予測の一貫性
        
        Returns:
        --------
        dict:
            各安定性指標値
        """
        return {
            'tc_cv': tc_cv,
            'tc_std': tc_std,
            'window_consistency': window_consistency
        }
    

    def _calculate_window_consistency(self, stability_metrics):
        """
        異なる時間窓での予測の一貫性を計算
        
        Parameters:
        -----------
        stability_metrics: tuple
            (tc_mean, tc_std, tc_cv) の形式のタプル
            
        Returns:
        --------
        float:
            予測の一貫性スコア (0から1)
        """
        # tc_mean（平均）とtc_cv（変動係数）を使用して一貫性を評価
        tc_mean, _, tc_cv = stability_metrics
        
        if tc_mean is None or tc_cv is None:
            return 0.0
            
        # 変動係数が小さいほど一貫性が高い
        # 典型的な変動係数の範囲（0～0.5）を0-1のスコアに変換
        consistency = max(0, 1 - 2 * tc_cv) if tc_cv is not None else 0
        
        return consistency





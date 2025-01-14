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
                         warning_level, start_date, end_date, plots_info):
        analysis_id = self.generate_analysis_id(symbol)
        
        tc, m, omega, phi, A, B, C = results
        current_time = len(data)
        days_to_tc = tc - current_time
        
        # 安定性分析による予測範囲を計算
        tc_mean, tc_std, tc_cv = stability_metrics
        if tc_mean is not None:
            mean_days_from_end = tc_mean - current_time
            predicted_mean_date = end_date + pd.Timedelta(days=int(mean_days_from_end))
            stability_range = {
                'start': (predicted_mean_date - pd.Timedelta(days=int(tc_std))).strftime('%Y年%m月%d日'),
                'end': (predicted_mean_date + pd.Timedelta(days=int(tc_std))).strftime('%Y年%m月%d日')
            }
        else:
            stability_range = {'start': None, 'end': None}

        analysis_summary = {
            'analysis_id': analysis_id,
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'critical_point': {
                'days_to_tc': float(days_to_tc),
                'predicted_date': (end_date + pd.Timedelta(days=int(days_to_tc))).strftime('%Y-%m-%d'),
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
            'quality_metrics': {
                'R2': float(quality_metrics['R2']),
                'RMSE': float(quality_metrics['RMSE']),
                'normality_p_value': float(quality_metrics['Residuals_normality_p']),
                'max_autocorr': float(quality_metrics['Max_autocorr'])
            },
            'stability_metrics': {
                'tc_mean': float(stability_metrics[0]) if stability_metrics[0] is not None else None,
                'tc_std': float(stability_metrics[1]) if stability_metrics[1] is not None else None,
                'tc_cv': float(stability_metrics[2]) if stability_metrics[2] is not None else None
            },
            'warning_level': warning_level,
            'plots': plots_info,
            'stability_range': stability_range, 
            'warning_level': warning_level,
            'plots': plots_info
        }
        
        # 結果をJSONファイルとして保存
        summary_path = os.path.join(self.base_dir, 'summaries', f'{analysis_id}_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_summary, f, indent=2, ensure_ascii=False)

        # CSVフォーマットの設定
        column_order = [
            'analysis_id',
            'symbol',
            'analysis_date',
            'days_to_tc',
            'predicted_date',
            'warning_level',
            'R2',
            'tc_cv',
            'm',
            'omega'
        ]            
        
        # CSVとしても保存（検索・フィルタリング用）
        df_summary = pd.DataFrame([{
            'analysis_id': analysis_id,
            'symbol': symbol,
            'analysis_date': analysis_summary['analysis_date'],
            'days_to_tc': round(analysis_summary['critical_point']['days_to_tc'], 2),  # 小数点2桁に制限
            'predicted_date': analysis_summary['critical_point']['predicted_date'],
            'warning_level': warning_level,
            'R2': round(quality_metrics['R2'], 3),  # 小数点3桁に制限
            'tc_cv': round(stability_metrics[2], 3) if stability_metrics[2] is not None else None,  # 小数点3桁に制限
            'm': round(results[1], 3),  # べき指数を追加
            'omega': round(results[2], 3)  # 角振動数を追加
        }])

        # 列の順序を指定
        df_summary = df_summary[column_order]
        
        # CSVファイルに保存
        csv_path = os.path.join(self.base_dir, 'metrics', 'analysis_records.csv')
        if os.path.exists(csv_path):
            df_summary.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            df_summary.to_csv(csv_path, index=False)
                
        return analysis_id
    
    def generate_report(self, analysis_id):
        """分析レポートを生成（予測手法の比較を含む）"""
        summary_path = os.path.join(self.base_dir, 'summaries', f'{analysis_id}_summary.json')
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        report = f"""
=== 対数周期性解析レポート ===
分析ID: {summary['analysis_id']}
銘柄: {summary['symbol']}
分析日時: {summary['analysis_date']}

【予測手法の比較】
1. 全期間フィッティング予測:
   臨界時点までの日数: {summary['critical_point']['days_to_tc']:.1f}日
   予測日: {summary['critical_point']['predicted_date']}

2. 安定性分析による予測:
   平均臨界時点までの日数: {summary['stability_metrics']['tc_mean']:.1f}日
   予測範囲: {summary['stability_range']['start']} ～ {summary['stability_range']['end']}
   信頼区間: ±{summary['stability_metrics']['tc_std']:.1f}日

【モデル品質指標】
R²スコア: {summary['quality_metrics']['R2']:.3f}
変動係数: {summary['stability_metrics']['tc_cv']:.3f}
警告レベル: {summary['warning_level']}

【総合評価】
{self._generate_evaluation(summary)}

分析グラフは {os.path.join(self.base_dir, 'plots')} に保存されています。
"""
        return report
            
    def _generate_evaluation(self, summary):
        """結果の評価コメントを生成（収束性分析を含む）"""
        evaluation = []
        
        main_prediction_date = datetime.strptime(summary['critical_point']['predicted_date'], '%Y-%m-%d')
        
        if summary['stability_metrics']['tc_mean'] is not None:
            stability_days = float(summary['stability_metrics']['tc_mean'])
            data_length = int(summary['critical_point']['parameters']['tc'] - summary['critical_point']['days_to_tc'])
            stability_date = datetime.strptime(summary['period']['end'], '%Y-%m-%d')
            stability_prediction = stability_date + timedelta(days=int(stability_days - data_length))
            
            date_diff = abs((main_prediction_date - stability_prediction).days)
            
            if date_diff < 14:
                evaluation.append(f"✓ 予測手法間の収束性が高い（差異: {date_diff}日）")
            elif date_diff < 30:
                evaluation.append(f"△ 予測手法間の収束性が中程度（差異: {date_diff}日）")
            else:
                evaluation.append(f"⚠ 予測手法間の収束性が低い（差異: {date_diff}日）")
            
        # 既存の評価項目を追加
        r2 = summary['quality_metrics']['R2']
        if r2 > 0.8:
            evaluation.append("✓ フィッティングの精度が高い (R² > 0.8)")
        elif r2 < 0.5:
            evaluation.append("⚠ フィッティングの精度が低い (R² < 0.5)")
        
        if summary['stability_metrics']['tc_cv'] is not None:
            cv = summary['stability_metrics']['tc_cv']
            if cv < 0.1:
                evaluation.append("✓ 予測が安定している (CV < 0.1)")
            elif cv > 0.3:
                evaluation.append("⚠ 予測の不確実性が高い (CV > 0.3)")
        
        if summary['warning_level'] == "高":
            evaluation.append("⚠ 近い将来に重要な変動が予測されます")
        
        return "\n".join(evaluation)

def get_latest_analyses(base_dir='analysis_results', n=5):
    """最新の分析結果を取得"""
    csv_path = os.path.join(base_dir, 'metrics', 'analysis_records.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df.sort_values('analysis_date', ascending=False).head(n)
    return None

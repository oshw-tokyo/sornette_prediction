import logging
import os
from datetime import datetime

class AnalysisFileHandler(logging.FileHandler):
    """分析結果をファイルに保存するハンドラー"""
    def __init__(self, base_dir='analysis_results', filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_{timestamp}.log'
        
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        super().__init__(os.path.join(log_dir, filename))

class RotatingAnalysisFileHandler(logging.handlers.RotatingFileHandler):
    """ローテーションありの分析ログハンドラー"""
    def __init__(self, base_dir='analysis_results', filename='analysis.log',
                 maxBytes=1024*1024, backupCount=5):
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        super().__init__(
            os.path.join(log_dir, filename),
            maxBytes=maxBytes,
            backupCount=backupCount
        )
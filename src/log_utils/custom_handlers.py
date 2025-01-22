# src/logging/custom_handlers.py
import logging
from logging import FileHandler 
import os
from datetime import datetime

class AnalysisFileHandler(FileHandler):  # logging.FileHandler から FileHandler に変更
    """分析結果をファイルに保存するハンドラー"""
    def __init__(self, base_dir='analysis_results', filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_{timestamp}.log'
        
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        super().__init__(os.path.join(log_dir, filename))

class RotatingAnalysisFileHandler(FileHandler):  # logging.FileHandler から FileHandler に変更
    """ローテーションありの分析ログハンドラー"""
    def __init__(self, base_dir='analysis_results', filename='analysis.log',
                 maxBytes=1024*1024, backupCount=5):
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        super().__init__(os.path.join(log_dir, filename))
        
        # ファイルサイズとバックアップ数の設定
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        
    def emit(self, record):
        """ログの出力とローテーション処理"""
        try:
            if self.should_rollover():
                self.do_rollover()
            super().emit(record)
        except Exception:
            self.handleError(record)
            
    def should_rollover(self):
        """ローテーションが必要かどうかを判断"""
        if not os.path.exists(self.baseFilename):
            return False
        if os.path.getsize(self.baseFilename) < self.maxBytes:
            return False
        return True
    
    def do_rollover(self):
        """ログファイルのローテーション処理"""
        if self.stream:
            self.stream.close()
            self.stream = None
            
        for i in range(self.backupCount - 1, 0, -1):
            sfn = f"{self.baseFilename}.{i}"
            dfn = f"{self.baseFilename}.{i + 1}"
            if os.path.exists(sfn):
                if os.path.exists(dfn):
                    os.remove(dfn)
                os.rename(sfn, dfn)
                
        dfn = self.baseFilename + ".1"
        if os.path.exists(dfn):
            os.remove(dfn)
        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dfn)
            
        if not self.delay:
            self.stream = self._open()
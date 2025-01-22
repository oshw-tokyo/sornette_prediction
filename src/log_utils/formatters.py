import logging

class AnalysisFormatter(logging.Formatter):
    """分析用のカスタムフォーマッター"""
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

class DetailedAnalysisFormatter(logging.Formatter):
    """詳細な分析情報用のフォーマッター"""
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s\n'
                'File: %(filename)s:%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
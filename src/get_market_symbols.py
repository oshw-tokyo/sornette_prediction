import pandas as pd
import json
import requests
from io import StringIO

def get_japan_listings():
    """東証上場銘柄の取得（xls形式対応）"""
    try:
        # ファイルをダウンロードして一時保存
        url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
        response = requests.get(url)
        
        with open('temp_jpx.xls', 'wb') as f:
            f.write(response.content)
            
        # xlrdでxlsファイルを読み込み
        df = pd.read_excel('temp_jpx.xls', engine='xlrd')
        
        # ETF・ETN以外の銘柄を抽出
        df = df[~df['市場・商品区分'].str.contains('ETF|ETN', na=False)]
        
        # コード列を4桁に整形し、.Tを付加
        df['銘柄コード'] = df['コード'].astype(str).str.zfill(4) + '.T'
        
        # 一時ファイルを削除
        import os
        os.remove('temp_jpx.xls')
        
        return df['銘柄コード'].tolist()
        
    except Exception as e:
        print(f"日本市場データの取得に失敗: {str(e)}")
        return []

def get_us_listings():
    """米国上場銘柄の取得"""
    try:
        # S&P500構成銘柄
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_table = pd.read_html(sp500_url)[0]
        sp500_symbols = sp500_table['Symbol'].tolist()

        # Nasdaq100構成銘柄
        nasdaq_url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        nasdaq_table = pd.read_html(nasdaq_url)[4]  # インデックスを4に変更
        nasdaq_symbols = nasdaq_table['Symbol'].tolist()  # 'Ticker'から'Symbol'に変更

        # 重複を除去して結合
        combined_symbols = list(set(sp500_symbols + nasdaq_symbols))
        
        # 無効な文字を含むシンボルを除外
        valid_symbols = [s for s in combined_symbols if isinstance(s, str) and '.' not in s]
        
        return valid_symbols
    except Exception as e:
        print(f"米国市場データの取得に失敗: {str(e)}")
        print(f"エラー詳細: ", traceback.format_exc())
        return []
    
def get_major_indices():
    """主要指数のティッカー"""
    return {
        'US': ['^GSPC', '^DJI', '^IXIC', '^RUT'],  # S&P500, ダウ, NASDAQ, Russell 2000
        'JP': ['^N225', '^TPX'],  # 日経225, TOPIX
        'ASIA': ['^HSI', '^STI', '^AXJO'],  # ハンセン, シンガポール, オーストラリア
        'EU': ['^FTSE', '^GDAXI', '^FCHI']  # FTSE, DAX, CAC
    }

def save_symbols():
    """銘柄リストの保存"""
    symbols = {
        'japan': get_japan_listings(),
        'us': get_us_listings(),
        'indices': get_major_indices()
    }
    
    with open('market_symbols.json', 'w') as f:
        json.dump(symbols, f, indent=2)

if __name__ == "__main__":
    save_symbols()
import time
import requests
from model import *
import datetime
import json
import os


def parse_data(data):
    ticker = data['ticker']
    for item in data['results']:
        new_stock = Stock()
        new_stock.name = ticker
        new_stock.price = item['c']

        dt_obj = datetime.datetime.fromtimestamp(item['t'] / 1000.0)
        date_str = dt_obj.date().isoformat()
        new_stock.date = date_str

        # check if already existed
        stock_where_cause = f'name=\'{ticker}\' and date=\'{date_str}\''
        stocks = Entity.filter(Stock, stock_where_cause)
        if len(stocks) > 0:
            print('skip', ticker, new_stock.price, new_stock.date)
            continue

        new_stock.save()
        print('insert', ticker, new_stock.price, new_stock.date)


def download_tick(ticker, start_date, end_date, api_key):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}?apiKey={api_key}"
    print(url)
    response = requests.get(url)
    data = response.json()
    return data


if __name__ == "__main__":
    start_date = '2018-04-18'
    end_date = '2023-04-18'
    api_keys = ['f6MtMuA0PhaA1Q3xTbd2TR6aGdf5ilSE', 'PQe6OK040zOQp38DYU1wOWIUmUdY8F7z']
    tickers = ["SPY", "MSFT", "NVDA", "INTC", "AMZN", "GOOGL", "FB", "TSM", "CSCO", "ADBE", "ORCL",
           "IBM", "AVGO", "TXN", "QCOM", "CRM", "PYPL", "SAP", "BABA", "BIDU", "TCEHY"]

    progress_file = "stocks.json"
    if os.path.exists(progress_file):
        progress = json.load(open(progress_file))
    else:
        progress = dict()

    count = 0
    for ticker in tickers:
        try:
            if ticker in progress:
                data = progress[ticker]
            else:
                data = download_tick(ticker, start_date, end_date, api_keys[count % 2])
                count += 1
                progress[ticker] = data
                time.sleep(10)
                
            parse_data(data)
                
        except:
            print(f"download {ticker} failed")

        json.dump(progress, open(progress_file, "w+"), indent=True)

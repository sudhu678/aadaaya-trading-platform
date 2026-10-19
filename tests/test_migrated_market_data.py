import pandas as pd
from market_data.bulk_provider import batch_download_universe, download_ticker_batch_with_retry
from market_data.utils import get_1d_series

def test_retries_and_returns():
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame() if len(calls)==1 else pd.DataFrame({'Close':[12]})
    result=download_ticker_batch_with_retry(['TEST'],downloader=fake,sleeper=lambda _:None)
    assert len(calls)==2 and result.iloc[0,0]==12

def test_batches_deduplicate():
    seen=[]
    def fake(**kwargs):
        seen.extend(kwargs['tickers'])
        return pd.DataFrame({'Close':[1]})
    batch_download_universe(['A','A','B','C'],batch_size=2,downloader=fake,sleeper=lambda _:None)
    assert seen==['A','B','C']

def test_get_1d_series_missing():
    assert get_1d_series(pd.DataFrame({'Close':[1,2]}),'Volume').empty

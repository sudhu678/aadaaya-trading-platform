import pandas as pd
import pytest
from market_data.sqlite_cache import DailyBarCache

def test_round_trip_and_upsert(tmp_path):
    cache = DailyBarCache(str(tmp_path / 'market.sqlite3'))
    bars = pd.DataFrame({'Open':[10.], 'High':[12.], 'Low':[9.], 'Close':[11.], 'Volume':[100.]}, index=pd.to_datetime(['2026-01-05']))
    assert cache.write('abc', bars) == 1
    assert cache.write('abc', bars) == 1
    result = cache.read('ABC','2026-01-01','2026-01-31')
    assert len(result) == 1 and result.iloc[0]['Close'] == 11

def test_ticker_isolation(tmp_path):
    cache = DailyBarCache(str(tmp_path / 'market.sqlite3'))
    bars = pd.DataFrame({'Open':[10], 'High':[12], 'Low':[9], 'Close':[11], 'Volume':[100]}, index=pd.to_datetime(['2026-01-05']))
    cache.write('ABC', bars)
    assert cache.read('XYZ','2026-01-01','2026-01-31').empty

def test_reject_invalid_bars(tmp_path):
    cache = DailyBarCache(str(tmp_path / 'market.sqlite3'))
    with pytest.raises(ValueError):
        cache.write('ABC', pd.DataFrame({'Close':[1]}, index=pd.to_datetime(['2026-01-05'])))

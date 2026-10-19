"""Public batch downloader with bounded retries; no private strategy dependencies."""
from __future__ import annotations
import time
import pandas as pd

def download_ticker_batch_with_retry(tickers, max_retries=3, backoff_factor=2.0, *, downloader=None, sleeper=time.sleep):
    if not tickers:
        return pd.DataFrame()
    if not 1 <= max_retries <= 10:
        raise ValueError('max_retries must be 1..10')
    if downloader is None:
        import yfinance as yf
        downloader = yf.download
    for attempt in range(max_retries):
        try:
            data = downloader(tickers=tickers, period='1y', interval='1d', group_by='ticker',
                              threads=True, progress=False, auto_adjust=False)
            if data is not None and not data.empty:
                return data
        except (OSError, RuntimeError, ValueError):
            pass
        if attempt + 1 < max_retries:
            sleeper(backoff_factor ** (attempt + 1))
    return pd.DataFrame()

def batch_download_universe(tickers, batch_size=50, delay_sec=0.5, *, downloader=None, sleeper=time.sleep):
    if batch_size < 1 or delay_sec < 0:
        raise ValueError('Invalid batch settings')
    tickers = list(dict.fromkeys(tickers))
    frames=[]
    for offset in range(0, len(tickers), batch_size):
        frame=download_ticker_batch_with_retry(tickers[offset:offset+batch_size],
                                               downloader=downloader, sleeper=sleeper)
        if not frame.empty:
            frames.append(frame)
        if offset + batch_size < len(tickers):
            sleeper(delay_sec)
    return pd.concat(frames, axis=1) if frames else pd.DataFrame()

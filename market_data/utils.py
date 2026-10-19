"""General-purpose OHLCV shape utilities (no trading rules)."""
import pandas as pd

def get_1d_series(df: pd.DataFrame, column_name: str) -> pd.Series:
    if column_name not in df.columns:
        return pd.Series(dtype=float)
    value = df[column_name]
    if isinstance(value, pd.DataFrame):
        value = value.iloc[:, 0]
    return value.squeeze()

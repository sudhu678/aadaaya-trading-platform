import pandas as pd
from adapters.dataframe_signal_adapter import PublicDataFrameScanner, COLUMNS

def test_empty_output_schema():
    scanner = PublicDataFrameScanner(lambda _: pd.DataFrame({'Close':[10.] * 60}))
    result = scanner.scan(['EXAMPLE'])
    assert list(result.columns) == COLUMNS
    assert result.empty

def test_explicit_tickers_required():
    scanner = PublicDataFrameScanner(lambda _: None)
    try:
        scanner.scan()
    except ValueError:
        pass
    else:
        raise AssertionError('must require tickers')

"""Portable JSON export of public educational backtest results."""
from __future__ import annotations
import json
from math import isfinite

def _validate(value):
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("Non-finite numeric result")
        return
    if isinstance(value, list):
        for item in value: _validate(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str): raise TypeError("JSON keys must be strings")
            _validate(item)
        return
    raise TypeError("Unsupported report value")

def build_json_report(result: dict) -> bytes:
    if not isinstance(result, dict) or not isinstance(result.get("results"), dict):
        raise ValueError("Invalid backtest result")
    _validate(result)
    return (json.dumps(result, indent=2, allow_nan=False, sort_keys=True) + "\n").encode("utf-8")

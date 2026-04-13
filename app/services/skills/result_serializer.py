"""Serialize arbitrary Python objects returned from the analysis sandbox."""
import math
from typing import Any


def serialize(obj: Any, max_rows: int = 50) -> Any:
    """Convert analysis result to a JSON-serialisable structure."""
    try:
        import pandas as pd  # noqa: PLC0415

        if isinstance(obj, pd.DataFrame):
            return obj.head(max_rows).to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.head(max_rows).to_dict()
    except ImportError:
        pass

    if isinstance(obj, dict):
        return {k: serialize(v, max_rows) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize(v, max_rows) for v in obj[:max_rows]]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj
    if isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    return str(obj)

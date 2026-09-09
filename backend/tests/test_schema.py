import pandas as pd
import pytest

from app.data.schema import CYCLE_COLUMNS, validate_cycles
from app.data.synthetic import generate_cell


def test_validate_sorts_and_selects_columns():
    df = generate_cell("X", 10).iloc[::-1]
    df["extra"] = 1
    out = validate_cycles(df)
    assert list(out.columns) == CYCLE_COLUMNS
    assert out["cycle"].is_monotonic_increasing


def test_validate_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing columns"):
        validate_cycles(pd.DataFrame({"cell_id": ["a"], "cycle": [1]}))


def test_validate_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        validate_cycles(pd.DataFrame(columns=CYCLE_COLUMNS))


def test_validate_rejects_nonpositive_capacity():
    df = generate_cell("X", 5)
    df.loc[0, "capacity_ah"] = 0
    with pytest.raises(ValueError, match="positive"):
        validate_cycles(df)


def test_validate_rejects_duplicates():
    df = generate_cell("X", 5)
    df = pd.concat([df, df.iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_cycles(df)

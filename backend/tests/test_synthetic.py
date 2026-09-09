from app.data.schema import CYCLE_COLUMNS
from app.data.synthetic import DEFAULT_CELLS, generate_cell, generate_dataset


def test_generate_cell_shape_and_columns():
    df = generate_cell("B0005", 50)
    assert len(df) == 50
    assert set(CYCLE_COLUMNS) <= set(df.columns)
    assert (df["cell_id"] == "B0005").all()


def test_capacity_fades_over_time():
    df = generate_cell("B0005", 150)
    assert df["capacity_ah"].iloc[:10].mean() > df["capacity_ah"].iloc[-10:].mean()


def test_generation_is_deterministic():
    a = generate_cell("B0005", 30, seed=3)
    b = generate_cell("B0005", 30, seed=3)
    assert a.equals(b)


def test_generate_dataset_contains_all_default_cells():
    df = generate_dataset(n_cycles=20)
    assert set(df["cell_id"]) == set(DEFAULT_CELLS)
    assert len(df) == 20 * len(DEFAULT_CELLS)

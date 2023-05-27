from pathlib import Path
import datetime

from cats.timeseries_conversion import cat_converter


TEST_DATA = Path(__file__).parent / "carbon_intensity_24h.csv"


def test_stub():
    pass


def test_timeseries_conversion():
    result = cat_converter(TEST_DATA)
    assert result == (
        datetime.datetime(2023, 5, 5, 14, 0),
        5.0,
    )

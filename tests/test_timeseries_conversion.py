from pathlib import Path
import datetime

import cats


TEST_DATA = Path(__file__).parent / "carbon_intensity_24h.csv"


def test_stub():
    pass


def test_timeseries_conversion():
    result = cats.cat_converter(TEST_DATA)
    assert result == {
        "timestamp": datetime.datetime(2023, 5, 5, 14, 0),
        "carbon_intensity": 5.0,
        "est_total_carbon": 5.0,
    }

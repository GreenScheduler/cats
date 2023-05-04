from pathlib import Path
import datetime

import cats


TEST_DATA = Path(__file__).parent / "carbon_intensity_24h.csv"

def test_stub():
    pass

def test_timeseries_conversion():
    result = cats.cat_converter(TEST_DATA)
    assert result == {'timestamp': datetime.datetime(2023, 5, 4, 12, 30), 'carbon_intensity': 2.0}
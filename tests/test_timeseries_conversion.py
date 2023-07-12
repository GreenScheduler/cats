from pathlib import Path
from datetime import datetime
import csv

from cats.optimise_starttime import get_starttime
from cats.forecast import CarbonIntensityPointEstimate


TEST_DATA = Path(__file__).parent / "carbon_intensity_24h.csv"


def test_stub():
    pass


def test_timeseries_conversion():
    with open(TEST_DATA, "r") as f:
        csvfile = csv.reader(f, delimiter=",")
        next(csvfile)  # Skip header line
        forecast_data = [
            CarbonIntensityPointEstimate(
                datetime=datetime.fromisoformat(datestr[:-1]),
                value=float(intensity_value),
            )
            for datestr, _, _, intensity_value in csvfile
        ]
    result = get_starttime(
        forecast_data, method="simple", duration=None
    )
    assert result == CarbonIntensityPointEstimate(
        datetime=datetime(2023, 5, 5, 14, 0),
        value=5.0,
    )

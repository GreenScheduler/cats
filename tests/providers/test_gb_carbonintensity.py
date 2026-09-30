from datetime import datetime
from unittest.mock import patch

import pytest

from cats.exceptions import InvalidLocationError, InvalidMetricError
from cats.forecast import PointEstimate
from cats.providers import GBCarbonIntensityProvider

# A real carbonintensity.org.uk regional response, captured live on
# 2026-09-29, used to test parsing offline/deterministically without
# depending on the live API.
RECORDED_RESPONSE = {
    "data": {
        "regionid": 12,
        "dnoregion": "SSE South",
        "shortname": "South England",
        "postcode": "OX1",
        "data": [
            {
                "from": "2026-09-29T11:30Z",
                "to": "2026-09-29T12:00Z",
                "intensity": {"forecast": 85, "index": "low"},
                "generationmix": [
                    {"fuel": "biomass", "perc": 6.1},
                    {"fuel": "coal", "perc": 0},
                    {"fuel": "imports", "perc": 9.5},
                    {"fuel": "gas", "perc": 17.7},
                    {"fuel": "nuclear", "perc": 4.0},
                    {"fuel": "other", "perc": 0},
                    {"fuel": "hydro", "perc": 0.2},
                    {"fuel": "solar", "perc": 28.5},
                    {"fuel": "wind", "perc": 34.0},
                ],
            }
        ],
    }
}


def test_get_data():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """

    timestamp = datetime.now()
    provider = GBCarbonIntensityProvider()
    response = provider.get_data(timestamp, "OX1")
    response_full_postcode = GBCarbonIntensityProvider().get_data(timestamp, "OX1 3QD")

    assert response == response_full_postcode
    assert isinstance(response.values, list)
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )


def test_get_data_renewables_metric():
    "carbon (default) and renewables come from the same underlying request"
    timestamp = datetime.now()
    provider = GBCarbonIntensityProvider()
    carbon = provider.get_data(timestamp, "OX1", metric="carbon")
    renewables = provider.get_data(timestamp, "OX1", metric="renewables")

    assert carbon.metric == "Carbon intensity"
    assert carbon.unit == "gCO2eq/kWh"
    assert renewables.metric == "Non-renewable share"
    assert renewables.unit == "%"
    assert len(renewables.values) > 0
    for item in renewables.values:
        assert -10.0 < item.value < 100.0


@patch("cats.providers.gb_carbonintensity.fetch_url")
def test_get_data_recorded_response(mock_fetch_url):
    "Parses a recorded response without hitting the network"
    mock_fetch_url.return_value = RECORDED_RESPONSE
    provider = GBCarbonIntensityProvider()

    carbon = provider.get_data(datetime.now(), "OX1", metric="carbon")
    assert len(carbon.values) == 1
    assert carbon.values[0].value == 85

    renewables = provider.get_data(datetime.now(), "OX1", metric="renewables")
    assert len(renewables.values) == 1
    # renewable = biomass(6.1) + hydro(0.2) + solar(28.5) + wind(34.0) = 68.8
    # non-renewable = 100 - 68.8 = 31.2
    assert renewables.values[0].value == pytest.approx(31.2)


def test_bad_metric():
    timestamp = datetime.now()
    provider = GBCarbonIntensityProvider()
    with pytest.raises(InvalidMetricError):
        _ = provider.get_data(timestamp, "OX1", metric="not_a_metric")


def test_bad_postcode():
    timestamp = datetime.now()
    provider = GBCarbonIntensityProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "OX40")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "A")


@pytest.mark.parametrize("outcode", ["BT1", "BT9 5AB", "GY1", "JE2"])
def test_postcodes_outside_gb_rejected(outcode):
    "Northern Ireland and the Channel Islands are not covered by the API"
    with pytest.raises(InvalidLocationError):
        _ = GBCarbonIntensityProvider().validate_location(outcode)


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = GBCarbonIntensityProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp)

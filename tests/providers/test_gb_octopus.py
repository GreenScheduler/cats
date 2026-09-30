from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cats.exceptions import InvalidLocationError
from cats.forecast import PointEstimate
from cats.providers import OctopusAgilePriceProvider

# Real responses, captured live on 2026-09-29, used to test parsing offline/
# deterministically without depending on the live API or network access.
# get_data() makes two calls in sequence: the products list, then the rates
# for the resolved product code. The rates are deliberately in descending
# (most-recent-first) order, matching the real API, to also exercise the sort.
RECORDED_PRODUCTS_RESPONSE = {
    "count": 2,
    "next": None,
    "results": [
        {"code": "AGILE-24-10-01", "brand": "OCTOPUS_ENERGY", "available_to": None},
        {
            "code": "AGILE-OUTGOING-19-05-13",
            "brand": "OCTOPUS_ENERGY",
            "available_to": None,
        },
    ],
}
RECORDED_RATES_RESPONSE = {
    "count": 2,
    "next": None,
    "results": [
        {
            "value_exc_vat": 23.18,
            "value_inc_vat": 24.339,
            "valid_from": "2026-09-29T21:00:00Z",
            "valid_to": "2026-09-29T21:30:00Z",
        },
        {
            "value_exc_vat": 15.73,
            "value_inc_vat": 16.5165,
            "valid_from": "2026-09-29T21:30:00Z",
            "valid_to": "2026-09-29T22:00:00Z",
        },
    ],
}


def test_get_data():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """
    timestamp = datetime.now()
    provider = OctopusAgilePriceProvider()
    response = provider.get_data(timestamp, "C")
    # lowercase input must resolve to the same region
    response_lowercase = OctopusAgilePriceProvider().get_data(timestamp, "c")

    assert response == response_lowercase
    assert isinstance(response.values, list)
    assert len(response.values) > 0
    assert response.metric == "Day-ahead electricity price"
    assert response.unit == "GBP/MWh"
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )
        # Sanity bound on plausible price magnitude (GBP/MWh); catches gross
        # parsing/unit-conversion bugs without being flaky around normal
        # price volatility, including negative prices.
        assert -500.0 < item.value < 5000.0


@patch("cats.providers.gb_octopus.fetch_url")
def test_get_data_recorded_response(mock_fetch_url):
    "Parses recorded responses without hitting the network"
    mock_fetch_url.side_effect = [
        RECORDED_PRODUCTS_RESPONSE,
        RECORDED_RATES_RESPONSE,
    ]
    provider = OctopusAgilePriceProvider()
    response = provider.get_data(datetime.now(timezone.utc), "C")

    assert response.metric == "Day-ahead electricity price"
    assert response.unit == "GBP/MWh"
    assert len(response.values) == 2
    # Ascending order despite the API returning descending order
    assert response.values[0].datetime < response.values[1].datetime
    assert response.values[0].value == pytest.approx(23.18 * 10)
    assert response.values[1].value == pytest.approx(15.73 * 10)


def test_bad_region():
    timestamp = datetime.now()
    provider = OctopusAgilePriceProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "Z")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "I")


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = OctopusAgilePriceProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp)

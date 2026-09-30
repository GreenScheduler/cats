from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cats.exceptions import InvalidLocationError, InvalidMetricError
from cats.forecast import PointEstimate
from cats.providers import EnergyChartsProvider

# A real /v2/price response, captured live on 2026-09-29, used to test parsing
# offline/deterministically without depending on the live API or network access.
RECORDED_PRICE_RESPONSE = {
    "unit": "EUR / MWh",
    "series": [{"id": "day_ahead_price", "name": "Day-ahead spot market price"}],
    "data": [
        {
            "timestamp": "2026-09-29T00:00:00+02:00",
            "values": {"day_ahead_price": 191.82},
        },
        {
            "timestamp": "2026-09-29T00:15:00+02:00",
            "values": {"day_ahead_price": 189.19},
        },
        {
            "timestamp": "2026-09-29T00:30:00+02:00",
            "values": {"day_ahead_price": 180.22},
        },
    ],
}
# A real /v2/signal response, captured live on 2026-09-29.
RECORDED_RENEWABLES_RESPONSE = {
    "unit": "%",
    "series": [
        {"id": "share", "name": "Renewable share of load"},
        {"id": "signal", "name": "Traffic signal"},
    ],
    "data": [
        {
            "timestamp": "2026-09-29T00:00:00+02:00",
            "values": {"share": 33.2, "signal": 0},
        },
        {
            "timestamp": "2026-09-29T00:15:00+02:00",
            "values": {"share": 34.0, "signal": 0},
        },
        # A real recorded value above 100%: renewable generation can exceed
        # domestic load around midday (surplus exported), which should
        # produce a negative "non-renewable share" rather than being clamped.
        {
            "timestamp": "2026-09-29T13:00:00+02:00",
            "values": {"share": 104.1, "signal": 2},
        },
    ],
}


def test_get_data_price():
    """
    This just checks the API call runs and returns a list of point estimates

    Also confirms that datetime objects are timezone aware, as per
    https://docs.python.org/3/library/datetime.html#determining-if-an-object-is-aware-or-naive
    """
    timestamp = datetime.now()
    provider = EnergyChartsProvider()
    response = provider.get_data(timestamp, "DE-LU", metric="price")
    # lowercase/alternate-case input must resolve to the same canonical zone
    response_lowercase = EnergyChartsProvider().get_data(
        timestamp, "de-lu", metric="price"
    )

    assert response == response_lowercase
    assert isinstance(response.values, list)
    assert len(response.values) > 0
    assert response.metric == "Day-ahead electricity price"
    assert response.unit == "EUR/MWh"
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )
        # Sanity bound on plausible day-ahead price magnitude (EUR/MWh);
        # catches gross parsing bugs without being flaky around normal
        # price volatility, including negative prices.
        assert -500.0 < item.value < 5000.0


def test_get_data_renewables():
    timestamp = datetime.now(timezone.utc)
    provider = EnergyChartsProvider()
    response = provider.get_data(timestamp, "de", metric="renewables")

    assert response.metric == "Non-renewable share"
    assert response.unit == "%"
    assert len(response.values) > 0
    for item in response.values:
        assert isinstance(item, PointEstimate)
        # Values can legitimately be negative (see RECORDED_RENEWABLES_RESPONSE
        # note), but should never be implausibly large in either direction.
        assert -100.0 < item.value < 100.0


@patch("cats.providers.eu_energycharts.fetch_url")
def test_get_data_price_recorded_response(mock_fetch_url):
    "Parses a recorded response without hitting the network"
    mock_fetch_url.return_value = RECORDED_PRICE_RESPONSE
    provider = EnergyChartsProvider()
    response = provider.get_data(datetime.now(timezone.utc), "DE-LU", metric="price")

    assert response.metric == "Day-ahead electricity price"
    assert response.unit == "EUR/MWh"
    assert len(response.values) == 3
    assert response.values[0].datetime == datetime.fromisoformat(
        "2026-09-29T00:00:00+02:00"
    )
    assert response.values[0].value == 191.82
    assert response.values[-1].value == 180.22
    # Ascending order by datetime
    assert [v.datetime for v in response.values] == sorted(
        v.datetime for v in response.values
    )


@patch("cats.providers.eu_energycharts.fetch_url")
def test_get_data_renewables_recorded_response(mock_fetch_url):
    "Parses a recorded response without hitting the network"
    mock_fetch_url.return_value = RECORDED_RENEWABLES_RESPONSE
    provider = EnergyChartsProvider()
    response = provider.get_data(datetime.now(timezone.utc), "de", metric="renewables")

    assert len(response.values) == 3
    assert response.values[0].value == pytest.approx(100 - 33.2)
    # share > 100% should yield a negative non-renewable share, not a clamp
    assert response.values[-1].value == pytest.approx(100 - 104.1)


def test_bad_metric():
    timestamp = datetime.now()
    provider = EnergyChartsProvider()
    with pytest.raises(InvalidMetricError):
        _ = provider.get_data(timestamp, "DE-LU", metric="not_a_metric")


def test_bad_zone():
    timestamp = datetime.now()
    provider = EnergyChartsProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "XX", metric="price")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "A", metric="price")


def test_bad_country():
    timestamp = datetime.now()
    provider = EnergyChartsProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "zz", metric="renewables")


@pytest.mark.parametrize(
    "country", ["uk", "xk", "ba", "cy", "ge", "ie", "md", "rs", "ua"]
)
def test_syntactically_valid_but_empty_countries_rejected(country):
    """
    These are accepted by the API's own query-parameter validation, but
    return an empty `data: []` (confirmed live on 2026-09-29), so
    EU_RENEWABLES_COUNTRIES deliberately excludes them.
    """
    timestamp = datetime.now(timezone.utc)
    provider = EnergyChartsProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, country, metric="renewables")


def test_cross_scheme_location_rejected():
    "A bidding zone isn't valid for renewables, and a country code isn't valid for price"
    timestamp = datetime.now()
    provider = EnergyChartsProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "de", metric="price")

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "DE-LU", metric="renewables")


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = EnergyChartsProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, metric="price")
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, metric="renewables")

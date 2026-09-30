import logging
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cats.exceptions import InvalidLocationError
from cats.forecast import PointEstimate, Timeseries
from cats.providers import CompositeProvider


def has_auth_env_setup():
    "Return True if both wattnet.eu email and password are set in the environment"
    email = os.environ.get("CATS_WATTNET_EMAIL", "")
    password = os.environ.get("CATS_WATTNET_PASSWORD", "")
    return (email != "") and (password != "")


# --- UK postcode kind: carbon/price/renewables come from carbonintensity.org.uk
# and octopus.energy, neither needing authentication, so these hit the real
# APIs directly (matching the existing no-mock style of
# tests/providers/test_uk_carbonintensity.py and tests/providers/test_gb_octopus.py).


def test_get_data_default_uses_all_three_no_auth_signals():
    """
    With no --signal given, a UK postcode combines carbon, price and
    renewables with equal weight, and never needs wattnet.eu credentials.
    """
    timestamp = datetime.now()
    provider = CompositeProvider()
    response = provider.get_data(timestamp, "OX1")

    assert isinstance(response.values, list)
    assert len(response.values) > 0
    assert (
        response.metric == "Composite score (carbon=0.33, price=0.33, renewables=0.33)"
    )
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )
        assert 0.0 <= item.value <= 1.0


def test_get_data_default_excludes_wattnet_signals(monkeypatch):
    """
    The default (no --signal) combination for a UK postcode must never
    require wattnet.eu credentials, even in an environment where they
    happen to be set.
    """
    monkeypatch.delenv("CATS_WATTNET_EMAIL", raising=False)
    monkeypatch.delenv("CATS_WATTNET_PASSWORD", raising=False)
    timestamp = datetime.now()
    provider = CompositeProvider()
    response = provider.get_data(timestamp, "OX1")

    assert (
        response.metric == "Composite score (carbon=0.33, price=0.33, renewables=0.33)"
    )


@pytest.mark.skipif(
    not has_auth_env_setup(),
    reason="No wattnet.eu authentication token found in environment",
)
def test_wattnet_signal_for_uk_postcode_falls_back_to_gb_zone_with_notice(caplog):
    """
    water, water_stress and environmental_score have no
    postcode-granular source, so for a UK postcode they fall back to
    wattnet.eu's fixed 'GB' zone, only when explicitly requested, with a
    logged notice about the substitution.
    """
    timestamp = datetime.now()
    provider = CompositeProvider(
        api_data={"signals": {"environmental_score": 0.5, "price": 0.5}}
    )
    with caplog.at_level(logging.WARNING):
        response = provider.get_data(timestamp, "OX1")

    assert response.metric == "Composite score (environmental_score=0.50, price=0.50)"
    assert len(response.values) > 0
    for item in response.values:
        assert 0.0 <= item.value <= 1.0
    assert any(
        "OX1" in record.message and "GB" in record.message for record in caplog.records
    )


def test_signal_extremes():
    """
    Selecting a single signal at weight 1 should exactly reproduce that
    signal's own normalised series.
    """
    timestamp = datetime.now()
    carbon_only = CompositeProvider(api_data={"signals": {"carbon": 1.0}})
    price_only = CompositeProvider(api_data={"signals": {"price": 1.0}})

    carbon_response = carbon_only.get_data(timestamp, "OX1")
    price_response = price_only.get_data(timestamp, "OX1")

    assert carbon_response.metric == "Composite score (carbon=1.00)"
    assert price_response.metric == "Composite score (price=1.00)"
    # The two extremes should generally differ from each other (carbon
    # intensity and price are not perfectly correlated), giving a basic
    # sanity check that signal selection is actually taking effect.
    assert [v.value for v in carbon_response.values] != [
        v.value for v in price_response.values
    ]


def test_signal_weights_are_normalised():
    "Weights that don't sum to 1 should be normalised automatically"
    timestamp = datetime.now()
    unnormalised = CompositeProvider(
        api_data={"signals": {"carbon": 2.0, "price": 2.0}}
    )
    normalised = CompositeProvider(api_data={"signals": {"carbon": 0.5, "price": 0.5}})

    unnormalised_response = unnormalised.get_data(timestamp, "OX1")
    normalised_response = normalised.get_data(timestamp, "OX1")

    assert unnormalised_response.metric == normalised_response.metric
    assert [v.value for v in unnormalised_response.values] == [
        v.value for v in normalised_response.values
    ]


def test_unknown_signal_raises_error():
    timestamp = datetime.now()
    provider = CompositeProvider(api_data={"signals": {"not_a_signal": 1.0}})
    with pytest.raises(ValueError):
        _ = provider.get_data(timestamp, "OX1")


def test_bad_postcode():
    "OX40 is neither a valid UK postcode outcode nor a wattnet.eu zone code"
    timestamp = datetime.now()
    provider = CompositeProvider()

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "OX40")


def test_missing_location_raises_error():
    timestamp = datetime.now()
    provider = CompositeProvider()
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp)


def test_ambiguous_code_prefers_uk_postcode():
    """
    'SE1'-'SE4' are both South East London UK postcodes and Swedish
    wattnet.eu price zones; the UK postcode interpretation always wins.
    """
    kind, canonical_location = CompositeProvider._detect_location("SE1")
    assert kind == "uk_postcode"
    assert canonical_location == "SE1"


# --- wattnet.eu zone kind: mocked at the get_data() level, since carbon/
# water/water_stress/environmental_score all need wattnet.eu
# credentials that are not available in this test environment. price/
# renewables (from energy-charts.info) are mocked alongside for consistency,
# even though they need no authentication.

FAKE_CARBON_TS = Timeseries(
    "Carbon intensity",
    values=[
        PointEstimate(
            value=100.0, datetime=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        ),
        PointEstimate(
            value=50.0, datetime=datetime(2026, 9, 29, 12, 15, tzinfo=timezone.utc)
        ),
    ],
    unit="gCO2eq/kWh",
)
FAKE_PRICE_TS = Timeseries(
    "Day-ahead electricity price",
    values=[
        PointEstimate(
            value=200.0, datetime=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        ),
        PointEstimate(
            value=100.0, datetime=datetime(2026, 9, 29, 12, 15, tzinfo=timezone.utc)
        ),
    ],
    unit="EUR/MWh",
)
FAKE_RENEWABLES_TS = Timeseries(
    "Non-renewable share",
    values=[
        PointEstimate(
            value=80.0, datetime=datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
        ),
        PointEstimate(
            value=40.0, datetime=datetime(2026, 9, 29, 12, 15, tzinfo=timezone.utc)
        ),
    ],
    unit="%",
)


def _fake_energycharts_get_data(timestamp, location, metric=None, headers=None):
    "Return price or renewables fake data depending on the requested metric"
    return FAKE_PRICE_TS if metric == "price" else FAKE_RENEWABLES_TS


@patch("cats.providers.composite.EnergyChartsProvider.get_data")
@patch("cats.providers.composite.WattnetEuProvider.get_data")
def test_wattnet_zone_default_uses_all_six_signals(
    mock_wattnet_get_data, mock_energycharts_get_data
):
    mock_wattnet_get_data.return_value = FAKE_CARBON_TS
    mock_energycharts_get_data.side_effect = _fake_energycharts_get_data

    provider = CompositeProvider()
    response = provider.get_data(datetime.now(timezone.utc), "DE")

    assert response.metric == (
        "Composite score (carbon=0.17, environmental_score=0.17, price=0.17, "
        "renewables=0.17, water=0.17, water_stress=0.17)"
    )
    assert response.unit == "0-1, lower=better"
    assert len(response.values) == 2
    for item in response.values:
        assert 0.0 <= item.value <= 1.0
    # carbon, water, water_stress, environmental_score
    assert mock_wattnet_get_data.call_count == 4
    # The energy-charts zone/country passed through should be the DE mappings
    assert mock_energycharts_get_data.call_count == 2
    called_locations = {
        call.kwargs["metric"]: call.args[1]
        for call in mock_energycharts_get_data.call_args_list
    }
    assert called_locations["price"] == "DE-LU"
    assert called_locations["renewables"] == "de"


@patch("cats.providers.composite.EnergyChartsProvider.get_data")
@patch("cats.providers.composite.WattnetEuProvider.get_data")
def test_wattnet_zone_signal_extremes(
    mock_wattnet_get_data, mock_energycharts_get_data
):
    mock_wattnet_get_data.return_value = FAKE_CARBON_TS
    mock_energycharts_get_data.side_effect = _fake_energycharts_get_data

    carbon_only = CompositeProvider(api_data={"signals": {"carbon": 1.0}})
    price_only = CompositeProvider(api_data={"signals": {"price": 1.0}})
    timestamp = datetime.now(timezone.utc)

    carbon_response = carbon_only.get_data(timestamp, "DE")
    price_response = price_only.get_data(timestamp, "DE")

    assert carbon_response.metric == "Composite score (carbon=1.00)"
    assert price_response.metric == "Composite score (price=1.00)"
    # Both extremes happen to agree here since carbon and price move together
    # in the fake data, but each should still be an exact 0/1 series.
    assert [v.value for v in carbon_response.values] == [1.0, 0.0]
    assert [v.value for v in price_response.values] == [1.0, 0.0]


@patch("cats.providers.composite.EnergyChartsProvider.get_data")
@patch("cats.providers.composite.WattnetEuProvider.get_data")
def test_wattnet_only_signal_combined_with_price(
    mock_wattnet_get_data, mock_energycharts_get_data
):
    "environmental_score (wattnet-only) combined with price (energy-charts-only)"
    mock_wattnet_get_data.return_value = FAKE_CARBON_TS
    mock_energycharts_get_data.side_effect = _fake_energycharts_get_data

    provider = CompositeProvider(
        api_data={"signals": {"environmental_score": 0.5, "price": 0.5}}
    )
    response = provider.get_data(datetime.now(timezone.utc), "ES")

    assert response.metric == "Composite score (environmental_score=0.50, price=0.50)"
    assert mock_wattnet_get_data.call_args.kwargs["metric"] == "environmental_score"
    assert mock_wattnet_get_data.call_args.args[1] == "ES"
    assert mock_energycharts_get_data.call_args.kwargs["metric"] == "price"
    assert mock_energycharts_get_data.call_args.args[1] == "ES"


@patch("cats.providers.composite.WattnetEuProvider.get_data")
def test_wattnet_zone_with_partial_signal_support_falls_back_by_default(
    mock_wattnet_get_data,
):
    """
    XK (Kosovo) is a valid wattnet.eu zone with the four wattnet-only
    signals (carbon, water, water_stress, environmental_score),
    but no energy-charts.info price or renewables equivalent. With no
    --signal given, the composite should silently fall back to the
    wattnet-only signals rather than failing.
    """
    mock_wattnet_get_data.return_value = FAKE_CARBON_TS
    provider = CompositeProvider()
    response = provider.get_data(datetime.now(timezone.utc), "XK")

    assert response.metric == (
        "Composite score (carbon=0.25, environmental_score=0.25, "
        "water=0.25, water_stress=0.25)"
    )


@patch("cats.providers.composite.WattnetEuProvider.get_data")
def test_gb_zone_code_defaults_to_wattnet_only_signals(mock_wattnet_get_data):
    """
    'GB' has no ambiguity with a UK postcode (it's not a valid outward code),
    so it is unambiguously the wattnet.eu 'GB' zone here, and behaves like
    any other zone with no energy-charts.info price/renewables equivalent.
    """
    mock_wattnet_get_data.return_value = FAKE_CARBON_TS
    provider = CompositeProvider()
    response = provider.get_data(datetime.now(timezone.utc), "GB")

    assert response.metric == (
        "Composite score (carbon=0.25, environmental_score=0.25, "
        "water=0.25, water_stress=0.25)"
    )


def test_explicit_signal_request_for_unavailable_zone_raises():
    "Explicitly requesting an unavailable signal must raise, not silently drop it"
    provider = CompositeProvider(api_data={"signals": {"price": 1.0}})
    timestamp = datetime.now(timezone.utc)

    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "XK")


def test_bad_zone():
    provider = CompositeProvider()
    timestamp = datetime.now(timezone.utc)
    with pytest.raises(InvalidLocationError):
        _ = provider.get_data(timestamp, "NOT_A_ZONE")


def test_resolve_signal():
    """
    resolve_signal() is the single-signal accessor used e.g. by
    cats/pricing.py. OX1's price signal routes to octopus.energy (no auth
    needed); XK (Kosovo) has no price signal at all, detected from the
    static WATTNET_TO_ENERGYCHARTS_ZONE lookup without any network call.
    """
    provider = CompositeProvider()
    timestamp = datetime.now()

    price = provider.resolve_signal("price", "OX1", timestamp)
    assert price is not None
    assert price.metric == "Day-ahead electricity price"

    assert provider.resolve_signal("price", "XK", timestamp) is None


@pytest.mark.skipif(
    not has_auth_env_setup(),
    reason="No wattnet.eu authentication token found in environment",
)
def test_get_data_live_wattnet_zone():
    """
    Live end-to-end check against all three real APIs (not mocked), covering
    the real WATTNET_TO_ENERGYCHARTS_ZONE mapping table, the wattnet-zone ->
    renewables-country derivation, and parsing.

    Only runs if CATS_WATTNET_EMAIL/CATS_WATTNET_PASSWORD are set, same as
    tests/providers/test_eu_wattnet.py.
    """
    timestamp = datetime.now(timezone.utc)
    provider = CompositeProvider()
    response = provider.get_data(timestamp, "DE")

    assert len(response.values) > 0
    for item in response.values:
        assert isinstance(item, PointEstimate)
        assert 0.0 <= item.value <= 1.0
        assert (item.datetime.tzinfo is not None) and (
            item.datetime.tzinfo.utcoffset(item.datetime) is not None
        )

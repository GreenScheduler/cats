import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cats.exceptions import InvalidLocationError, ProviderAuthenticationError
from cats.forecast import PointEstimate, WindowedForecast
from cats.providers import EIAProvider, ERCOTProvider
from cats.providers.us_grid import (
    EIA_FUELS,
    EMISSION_FACTORS,
    ERCOT_FUELS,
    carbon_intensity,
    persistence_forecast,
)

# ERCOT's public fuel-mix dashboard, captured live on 2026-11-15 at
# 19:13 CST and thinned to one point an hour to keep the file small.
ERCOT_SAMPLE = json.loads(
    (Path(__file__).parent / "ercot_fuel_mix_sample.json").read_text()
)
ERCOT_NOW = datetime(2026, 11, 16, 1, 7, tzinfo=timezone.utc)  # 19:07 CST


def hourly(start: datetime, values: list[float]) -> list[PointEstimate]:
    return [
        PointEstimate(datetime=start + timedelta(hours=i), value=v)
        for i, v in enumerate(values)
    ]


def test_carbon_intensity_weights_by_generation():
    mix = {"Coal and Lignite": 1.0, "Wind": 3.0}
    expected = (820.0 * 1 + 11.0 * 3) / 4
    assert carbon_intensity(mix, ERCOT_FUELS) == pytest.approx(expected)


def test_carbon_intensity_ignores_charging_and_counts_storage_as_zero():
    mix = {"Natural Gas": 100.0, "Power Storage": -50.0}
    assert carbon_intensity(mix, ERCOT_FUELS) == pytest.approx(490.0)
    mix = {"Natural Gas": 100.0, "Power Storage": 100.0}
    assert carbon_intensity(mix, ERCOT_FUELS) == pytest.approx(245.0)


def test_carbon_intensity_unknown_fuel_counts_as_other():
    assert carbon_intensity({"XYZ": 1.0}, EIA_FUELS) == EMISSION_FACTORS["other"]


def test_carbon_intensity_needs_positive_generation():
    with pytest.raises(ValueError):
        carbon_intensity({"Wind": 0.0, "Power Storage": -10.0}, ERCOT_FUELS)


def test_every_mapped_fuel_has_a_factor():
    for fuels in (ERCOT_FUELS, EIA_FUELS):
        assert set(fuels.values()) <= set(EMISSION_FACTORS)


def test_persistence_forecast_repeats_yesterday():
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    history = hourly(start, [float(i) for i in range(48)])
    forecast = persistence_forecast(
        history, start + timedelta(days=2), timedelta(hours=1)
    )
    assert len(forecast) == 25
    assert [p.value for p in forecast[:24]] == [float(i) for i in range(24, 48)]
    assert forecast[0].datetime == start + timedelta(days=2)


def test_persistence_forecast_falls_back_to_latest_published_day():
    # The last 3 hours of the most recent day are not published yet
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    history = hourly(start, [float(i) for i in range(45)])
    forecast = persistence_forecast(
        history, start + timedelta(days=2), timedelta(hours=1)
    )
    assert forecast[20].value == 44.0  # one day back
    assert forecast[21].value == 21.0  # two days back


def test_persistence_forecast_averages_days():
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    history = hourly(start, [10.0] * 24 + [20.0] * 24)
    forecast = persistence_forecast(
        history, start + timedelta(days=2), timedelta(hours=1), days=2
    )
    assert forecast[0].value == pytest.approx(15.0)


def test_persistence_forecast_matches_offset_timestamps():
    start = datetime(2025, 6, 1, 0, 0, 57, tzinfo=timezone.utc)
    history = hourly(start - timedelta(minutes=1), [1.0, 2.0, 3.0])
    forecast = persistence_forecast(
        history,
        datetime(2025, 6, 2, tzinfo=timezone.utc),
        timedelta(hours=1),
        horizon=timedelta(hours=2),
    )
    assert [p.value for p in forecast] == [1.0, 2.0, 3.0]


def test_persistence_forecast_empty_history():
    assert persistence_forecast([], ERCOT_NOW, timedelta(hours=1)) == []


def test_ercot_location():
    provider = ERCOTProvider()
    assert provider.validate_location("ercot") == "ERCOT"
    with pytest.raises(InvalidLocationError):
        provider.validate_location("TX")
    with pytest.raises(InvalidLocationError):
        provider.validate_location(None)
    for group in provider.list_locations():
        for code in group.locations:
            assert provider.validate_location(code) == code


def test_ercot_observed_values_are_plausible():
    points = ERCOTProvider().observed(ERCOT_SAMPLE)
    assert len(points) == 44
    assert points == sorted(points, key=lambda p: p.datetime)
    for p in points:
        assert p.datetime.tzinfo is not None
        assert 0.0 < p.value < 820.0


@patch("cats.providers.us_grid.fetch_url")
def test_ercot_get_data_recorded_response(mock_fetch_url):
    mock_fetch_url.return_value = ERCOT_SAMPLE
    provider = ERCOTProvider()
    forecast = provider.get_data(ERCOT_NOW, "ERCOT")

    url = mock_fetch_url.call_args.args[0]
    assert url.startswith(
        "https://www.ercot.com/api/1/services/read/dashboards/fuel-mix.json?"
    )
    assert "t=2026-11-16T01%3A05Z" in url
    assert forecast.metric == "Carbon intensity"
    assert forecast.unit == "gCO2eq/kWh"
    values = forecast.values
    aligned = datetime(2026, 11, 16, 1, 5, tzinfo=timezone.utc)
    # The sample has one point an hour, so only times whose previous-day
    # point lies within one 5 minute step are forecast: one an hour here
    assert aligned <= values[0].datetime < aligned + timedelta(hours=1)
    assert all(p.datetime.minute % 5 == 0 for p in values)
    assert values == sorted(values, key=lambda p: p.datetime)
    assert values[-1].datetime <= aligned + timedelta(hours=24)
    assert len(values) == 24
    assert all(0.0 < p.value < 820.0 for p in values)


@patch("cats.providers.us_grid.fetch_url")
def test_ercot_forecast_works_with_windowed_search(mock_fetch_url):
    mock_fetch_url.return_value = ERCOT_SAMPLE
    forecast = ERCOTProvider().get_data(ERCOT_NOW, "ERCOT")
    hourly_points = forecast.values[::12]
    wf = WindowedForecast(hourly_points, 120, start=hourly_points[0].datetime)
    best = min(wf)
    assert best.value <= wf[0].value


def eia_response(start: datetime, hours: int, coal: float, wind: float) -> dict:
    """Rows in the documented shape of the EIA v2 fuel-type-data endpoint

    Periods are UTC hour-ending, as in EIA-930. This is a constructed
    response, since the live API needs a key.
    """
    rows = []
    for i in range(hours):
        period = (start + timedelta(hours=i + 1)).strftime("%Y-%m-%dT%H")
        rows.append(
            {
                "period": period,
                "respondent": "ERCO",
                "fueltype": "COL",
                "value": coal + i,
            }
        )
        rows.append(
            {"period": period, "respondent": "ERCO", "fueltype": "WND", "value": wind}
        )
        rows.append(
            {"period": period, "respondent": "ERCO", "fueltype": "BAT", "value": -5}
        )
    return {"response": {"data": rows}}


def test_eia_location():
    provider = EIAProvider()
    assert provider.validate_location("erco") == "ERCO"
    with pytest.raises(InvalidLocationError):
        provider.validate_location("TEXAS")
    for group in provider.list_locations():
        for code in group.locations:
            assert provider.validate_location(code) == code


def test_eia_needs_api_key(monkeypatch):
    monkeypatch.delenv("CATS_EIA_API_KEY", raising=False)
    with pytest.raises(ProviderAuthenticationError):
        EIAProvider().get_data(ERCOT_NOW, "ERCO")


def test_eia_periods_are_hour_ending():
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    points = EIAProvider.observed(eia_response(start, 2, 100.0, 100.0))
    assert [p.datetime for p in points] == [start, start + timedelta(hours=1)]
    assert points[0].value == pytest.approx((820 * 100 + 11 * 100) / 200)


def test_eia_ignores_all_sources_total():
    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    response = eia_response(start, 1, 100.0, 100.0)
    response["response"]["data"].append(
        {
            "period": "2025-06-01T01",
            "respondent": "ERCO",
            "fueltype": "SYS",
            "value": 200,
        }
    )
    points = EIAProvider.observed(response)
    assert points[0].value == pytest.approx((820 * 100 + 11 * 100) / 200)


@patch("cats.providers.us_grid.fetch_url")
def test_eia_get_data(mock_fetch_url, monkeypatch):
    monkeypatch.setenv("CATS_EIA_API_KEY", "test-key")
    now = datetime(2025, 6, 3, 12, 30, tzinfo=timezone.utc)
    history_start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    mock_fetch_url.return_value = eia_response(history_start, 59, 100.0, 300.0)

    forecast = EIAProvider().get_data(now, "erco")

    url = mock_fetch_url.call_args.args[0]
    assert url.startswith(
        "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/?"
    )
    assert "api_key=test-key" in url
    assert "facets%5Brespondent%5D%5B%5D=ERCO" in url
    assert "start=2025-05-25T12" in url  # 7 days plus 2 spare
    values = forecast.values
    assert values[0].datetime == datetime(2025, 6, 3, 12, tzinfo=timezone.utc)
    # 12:00 today is the mean of 12:00 on the published days (only two here)
    observed = {
        p.datetime: p.value for p in EIAProvider.observed(mock_fetch_url.return_value)
    }
    expected = (
        observed[datetime(2025, 6, 2, 12, tzinfo=timezone.utc)]
        + observed[datetime(2025, 6, 1, 12, tzinfo=timezone.utc)]
    ) / 2
    assert values[0].value == pytest.approx(expected)
    assert values[-1].datetime == datetime(2025, 6, 4, 12, tzinfo=timezone.utc)

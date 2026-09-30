from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cats.exceptions import PriceConstraintUnsatisfiableError
from cats.forecast import PointEstimate, Timeseries, WindowedForecast
from cats.pricing import (
    find_best_within_price_constraint,
    price_at_window,
    price_covers_window,
    resolve_price_series,
)
from cats.providers.composite import CompositeProvider
from cats.providers.eu_wattnet import WattnetEuProvider
from cats.providers.uk_carbonintensity import UKCarbonIntensityProvider

D = datetime(2026, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(minutes=30)
DURATION = 30  # == STEP, so each window is a simple average of one consecutive pair


def series(values: list[float], start: datetime = D, step: timedelta = STEP):
    return [
        PointEstimate(value=v, datetime=start + i * step) for i, v in enumerate(values)
    ]


def test_price_at_window_averages_over_the_given_window():
    # With duration == the data's own step size, the window spans exactly one
    # consecutive pair of points, so the average is their simple mean.
    prices = series([100.0, 100.0, 200.0])
    assert price_at_window(prices, D, duration=DURATION) == pytest.approx(100.0)


def test_price_covers_window():
    prices = series([1.0, 2.0, 3.0])  # D, D+30min, D+60min
    assert price_covers_window(prices, D, D + timedelta(minutes=60))
    assert not price_covers_window(prices, D, D + timedelta(minutes=90))
    assert not price_covers_window(prices, D - timedelta(minutes=30), D)
    assert not price_covers_window([], D, D + timedelta(minutes=30))


def test_max_price_excludes_the_global_carbon_optimum():
    """
    With duration == step, window i is the simple average of (carbon[i],
    carbon[i+1]). carbon = [50,100,100,100,5,6,100,100] gives a unique
    global minimum at window 3 (pair (5, 6) -> avg 5.5, the lowest of all six
    windows) starting at D+90min. Its matching price window is priced high
    (300); capping price at 150 must exclude it, falling back to the next
    best carbon window that fits under the cap.
    """
    carbon = [100, 100, 100, 5, 6, 100, 100]
    price = [100, 100, 100, 100, 500, 500, 100]
    carbon_ts = series(carbon)
    price_ts = series(price)
    wf = WindowedForecast(carbon_ts, duration=DURATION, start=D)

    unconstrained = min(wf)
    assert unconstrained.start_value == 5  # sanity check on the test data
    assert unconstrained.start == D + timedelta(minutes=90)

    best = find_best_within_price_constraint(
        wf, price_ts, duration=DURATION, max_price=150, max_price_increase_pct=None
    )
    assert best.start != unconstrained.start
    assert best.start_value != 5


def test_max_price_increase_pct_relative_to_now():
    """
    "Now" (window 0) is priced at 100; a 50% cap allows up to 150. The
    unconstrained carbon optimum is window 1 (pair (10, 5) -> avg 7.5,
    starting at D+30min), but its price window (pair (100, 300) -> avg 200)
    exceeds the cap, so it must be excluded.
    """
    carbon = [50, 10, 5, 40, 50]
    price = [100, 100, 300, 100, 100]
    carbon_ts = series(carbon)
    price_ts = series(price)
    wf = WindowedForecast(carbon_ts, duration=DURATION, start=D)

    unconstrained = min(wf)
    assert unconstrained.start_value == 10
    assert unconstrained.start == D + timedelta(minutes=30)

    best = find_best_within_price_constraint(
        wf, price_ts, duration=DURATION, max_price=None, max_price_increase_pct=50
    )
    assert best.start != unconstrained.start
    assert best.start_value != 10


def test_unsatisfiable_constraint_raises():
    carbon = series([50, 40, 30])
    price = series([1000, 1000, 1000])
    wf = WindowedForecast(carbon, duration=DURATION, start=D)

    with pytest.raises(PriceConstraintUnsatisfiableError):
        find_best_within_price_constraint(
            wf, price, duration=DURATION, max_price=1.0, max_price_increase_pct=None
        )


def test_carbon_optimum_beyond_price_horizon_is_excluded_not_erroring():
    """
    carbon = [100,100,100,20,5,3,100] has its global optimum at window 4
    (pair (5, 3) -> avg 4, starting at D+120min), but price data only covers
    up to D+60min. Any window whose [start, end] extends past that horizon
    (windows 2-5) must be silently excluded from the search rather than
    raising, leaving only windows 0 and 1 eligible.
    """
    carbon = series([100, 100, 100, 20, 5, 3, 100])
    price = series([100, 100, 100])  # only covers up to D + 60min
    wf = WindowedForecast(carbon, duration=DURATION, start=D)

    unconstrained = min(wf)
    assert unconstrained.start_value == 5

    best = find_best_within_price_constraint(
        wf, price, duration=DURATION, max_price=1_000_000, max_price_increase_pct=None
    )
    assert best.start_value != 5
    assert price_covers_window(price, best.start, best.end)


def test_now_without_price_coverage_is_unsatisfiable_for_relative_cap():
    "A relative-to-now cap is meaningless if 'now' itself has no price data"
    carbon = series([50, 40, 30])
    wf = WindowedForecast(carbon, duration=DURATION, start=D)
    price = series([100.0], start=D + timedelta(hours=5))  # no overlap with "now"

    with pytest.raises(PriceConstraintUnsatisfiableError):
        find_best_within_price_constraint(
            wf, price, duration=DURATION, max_price=None, max_price_increase_pct=50
        )


@patch("cats.pricing.CompositeProvider")
def test_resolve_price_series_returns_none_when_no_price_signal(mock_composite_cls):
    mock_composite_cls.return_value.resolve_signal.return_value = None
    assert resolve_price_series("XK", D) is None
    mock_composite_cls.return_value.resolve_signal.assert_called_once_with(
        "price", "XK", D, assume_kind=None
    )


@patch("cats.pricing.CompositeProvider")
def test_resolve_price_series_fetches_price_signal(mock_composite_cls):
    price_ts = Timeseries(
        "Day-ahead electricity price",
        values=[PointEstimate(value=100.0, datetime=D)],
        unit="EUR/MWh",
    )
    mock_composite_cls.return_value.resolve_signal.return_value = price_ts

    result = resolve_price_series("DE", D)

    assert result is price_ts
    mock_composite_cls.return_value.resolve_signal.assert_called_once_with(
        "price", "DE", D, assume_kind=None
    )


@patch("cats.pricing.CompositeProvider")
def test_resolve_price_series_passes_assume_kind_for_single_scheme_providers(
    mock_composite_cls,
):
    """
    'SE1' is valid both as a South East London postcode and as a Swedish
    wattnet.eu zone. When the primary provider is WattnetEuProvider (which
    only ever accepts wattnet.eu zone codes), price must be resolved for the
    same zone, not composite's own postcode-priority guess.
    """
    mock_composite_cls.return_value.resolve_signal.return_value = None

    resolve_price_series("SE1", D, provider_cls=WattnetEuProvider)
    mock_composite_cls.return_value.resolve_signal.assert_called_with(
        "price", "SE1", D, assume_kind="wattnet_zone"
    )

    resolve_price_series("SE1", D, provider_cls=UKCarbonIntensityProvider)
    mock_composite_cls.return_value.resolve_signal.assert_called_with(
        "price", "SE1", D, assume_kind="uk_postcode"
    )

    # A provider without a single unambiguous location scheme (e.g.
    # composite itself, or octopus.energy's own region-letter scheme) falls
    # back to plain auto-detection, unchanged.
    resolve_price_series("SE1", D, provider_cls=CompositeProvider)
    mock_composite_cls.return_value.resolve_signal.assert_called_with(
        "price", "SE1", D, assume_kind=None
    )

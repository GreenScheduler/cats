"""
Price as an optional scheduling constraint, not a blended optimisation weight

Lets a caller cap the day-ahead electricity price of the chosen job start time
(via --max-price or --max-price-increase-pct in cli.py), independently of
whichever metric/provider is actually being optimised on, and always reports
the price impact of the chosen schedule when price data is available for the
location. Reuses composite.py's existing location-aware price routing (GB
postcode -> octopus.energy, wattnet.eu zone -> energy-charts.info) rather than
duplicating it.
"""

from datetime import datetime

from .exceptions import PriceConstraintUnsatisfiableError
from .forecast import AverageEstimate, PointEstimate, Timeseries, WindowedForecast
from .providers.base import BaseProvider
from .providers.composite import CompositeProvider
from .providers.eu_wattnet import WattnetEuProvider
from .providers.uk_carbonintensity import UKCarbonIntensityProvider

# Providers whose location argument unambiguously means one specific kind of
# composite location scheme. Used so that e.g. `--api wattnet.eu --location
# SE1` resolves price for the Swedish wattnet.eu zone SE1, not composite's
# own postcode-priority guess (which would silently pick the South East
# London postcode instead - a completely different location). Providers not
# listed here (octopus.energy's own region-letter scheme, energy-charts.info's
# own native bidding-zone codes, or composite itself, which already does its
# own equivalent auto-detection on the same location string) fall back to
# plain auto-detection.
PROVIDER_LOCATION_KIND: dict[type[BaseProvider], str] = {
    UKCarbonIntensityProvider: "uk_postcode",
    WattnetEuProvider: "wattnet_zone",
}


def resolve_price_series(
    location: str,
    timestamp: datetime,
    provider_cls: type[BaseProvider] | None = None,
) -> Timeseries | None:
    """
    Get a day-ahead price series for any location composite understands

    :param location: A UK postcode outward code or a wattnet.eu zone code
    :param timestamp: Timestamp from which to start forecast data retrieval
    :param provider_cls: The provider actually selected for the main
        forecast (via --api), if any. When it unambiguously implies one
        location kind (see PROVIDER_LOCATION_KIND), that kind is used
        directly instead of auto-detecting it from scratch, so an
        ambiguous code isn't silently reinterpreted as the other kind.
    :return: The price Timeseries, or None if this location has no price signal
    :raises InvalidLocationError: if `location` matches neither scheme at all
    """
    assume_kind = PROVIDER_LOCATION_KIND.get(provider_cls) if provider_cls else None
    return CompositeProvider().resolve_signal(
        "price", location, timestamp, assume_kind=assume_kind
    )


def price_covers_window(
    price_values: list[PointEstimate], window_start: datetime, window_end: datetime
) -> bool:
    "Whether the price series has real data spanning the entire [window_start, window_end]"
    if not price_values:
        return False
    return (
        window_start >= price_values[0].datetime
        and window_end <= price_values[-1].datetime
    )


def price_at_window(
    price_values: list[PointEstimate], window_start: datetime, duration: int
) -> float:
    "Average price over one arbitrary [window_start, window_start + duration] window"
    return WindowedForecast(
        price_values, duration, start=window_start, max_window_minutes=duration
    )[0].value


def find_best_within_price_constraint(
    wf: WindowedForecast,
    price_values: list[PointEstimate],
    duration: int,
    max_price: float | None,
    max_price_increase_pct: float | None,
) -> AverageEstimate:
    """
    Pick the minimum-value window in `wf` whose price satisfies the given cap

    Candidate windows whose [start, end] falls outside the price series'
    actual coverage are excluded from the search (their price cannot be
    verified against the cap at all), rather than raising - this naturally
    caps the effective search horizon to whatever price data currently covers.

    :raises PriceConstraintUnsatisfiableError: if no candidate window both
        falls within price data's horizon and satisfies the price cap
    """
    if max_price is not None:
        cap = max_price
    else:
        assert max_price_increase_pct is not None, (
            "Must give one of max_price or max_price_increase_pct"
        )
        now = wf[0]
        if not price_covers_window(price_values, now.start, now.end):
            raise PriceConstraintUnsatisfiableError(
                "No price data available for the current window; "
                "--max-price-increase-pct needs a price for 'now' to compare against"
            )
        price_now = price_at_window(price_values, now.start, duration)
        cap = price_now * (1 + max_price_increase_pct / 100)

    eligible = [
        estimate
        for estimate in wf
        if price_covers_window(price_values, estimate.start, estimate.end)
        and price_at_window(price_values, estimate.start, duration) <= cap
    ]
    if not eligible:
        raise PriceConstraintUnsatisfiableError(
            f"No candidate start time both falls within price data's forecast "
            f"horizon and satisfies the price constraint (cap={cap:.2f}); try "
            "relaxing --max-price/--max-price-increase-pct or removing it."
        )
    return min(eligible)

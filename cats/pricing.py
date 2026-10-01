"""
Price as an optional scheduling constraint, not a blended optimisation weight

Lets a caller cap the day-ahead electricity price of the chosen job start time
(via --max-price or --max-price-increase-pct in cli.py), independently of
whichever metric/provider is actually being optimised on, and always reports
the price impact of the chosen schedule when price data is available for the
location. The location can be a GB postcode (priced by octopus.energy) or a
wattnet.eu zone code (priced by energy-charts.info).
"""

from datetime import datetime
from typing import Any

from .exceptions import InvalidLocationError, PriceConstraintUnsatisfiableError
from .forecast import AverageEstimate, PointEstimate, Timeseries, WindowedForecast
from .providers.base import BaseProvider, align_to_resolution, fetch_url
from .providers.eu_energycharts import EnergyChartsProvider
from .providers.eu_wattnet import WattnetEuProvider
from .providers.gb_carbonintensity import GBCarbonIntensityProvider
from .providers.gb_octopus import OctopusAgilePriceProvider

# NESO's carbonintensity.org.uk regional API resolves a postcode to one of 14
# numbered GB distribution regions (see the "regionid"/"shortname" fields in
# its response) which are the *same* 14 regions used by Octopus Energy's
# Agile tariff, just identified differently (a number + English name, vs. a
# single letter). This maps NESO's regionid directly onto the Octopus region
# letter, confirmed against a live regional listing from both APIs on
# 2026-09-29.
REGIONID_TO_OCTOPUS_LETTER: dict[int, str] = {
    1: "P",  # North Scotland
    2: "N",  # South Scotland
    3: "G",  # North West England
    4: "F",  # North East England
    5: "M",  # Yorkshire
    6: "D",  # North Wales & Merseyside / Merseyside & Northern Wales
    7: "K",  # South Wales
    8: "E",  # West Midlands
    9: "B",  # East Midlands
    10: "A",  # East England
    11: "L",  # South West England
    12: "H",  # South England
    13: "C",  # London
    14: "J",  # South East England
}

# wattnet.eu zone -> energy-charts.info bidding zone, for the "price" signal
# when the location is a wattnet.eu zone. The two providers use different
# naming schemes for what is otherwise the same real-world zone (e.g.
# wattnet's "IT_NORTH" vs energy-charts's "IT-North"), so this has to be a
# static table, built by inspecting cats/data/wattnet_zones.txt and
# cats/data/energycharts_zones.txt on 2026-09-29.
#
# Not every wattnet zone has an entry here. Zones excluded, and why:
# - GB: not on energy-charts.info at all (see eu_energycharts.py). A GB
#   *postcode* location still gets price via octopus.energy; only the
#   wattnet zone code "GB" specifically lacks a price signal here.
# - BA, CY, GE, MD, MK, TR, XK: non-EU/EEA zones with no energy-charts.info
#   day-ahead price equivalent.
# - LU: energy-charts only publishes the merged "DE-LU" bidding zone (Germany
#   and Luxembourg have been price-coupled since 2018), not standalone
#   Luxembourg; wattnet's separate DE and LU entries both map to it, which is
#   why DE-LU appears twice below.
# - IE and NIE (Northern Ireland) both map to the same energy-charts zone:
#   Ireland and Northern Ireland trade on a single all-island day-ahead
#   market (SEM), which energy-charts lists as "IE(SEM)".
WATTNET_TO_ENERGYCHARTS_ZONE: dict[str, str] = {
    "AT": "AT",
    "BE": "BE",
    "BG": "BG",
    "CH": "CH",
    "CZ": "CZ",
    "DE": "DE-LU",
    "DK1": "DK1",
    "DK2": "DK2",
    "EE": "EE",
    "ES": "ES",
    "FI": "FI",
    "FR": "FR",
    "GR": "GR",
    "HR": "HR",
    "HU": "HU",
    "IE": "IE(SEM)",
    "NIE": "IE(SEM)",
    "IT_CALABRIA": "IT-Calabria",
    "IT_CNORTH": "IT-Centre-North",
    "IT_CSOUTH": "IT-Centre-South",
    "IT_NORTH": "IT-North",
    "IT_SARDINIA": "IT-Sardinia",
    "IT_SICILY": "IT-Sicily",
    "IT_SOUTH": "IT-South",
    "LT": "LT",
    "LV": "LV",
    "ME": "ME",
    "NL": "NL",
    "NO1": "NO1",
    "NO2": "NO2",
    "NO3": "NO3",
    "NO4": "NO4",
    "NO5": "NO5",
    "PL": "PL",
    "PT": "PT",
    "RO": "RO",
    "RS": "RS",
    "SE1": "SE1",
    "SE2": "SE2",
    "SE3": "SE3",
    "SE4": "SE4",
    "SI": "SI",
    "SK": "SK",
}

# Providers whose location argument unambiguously means one specific kind of
# location scheme. Used so that e.g. `--api wattnet.eu --location SE1`
# resolves price for the Swedish wattnet.eu zone SE1, not the postcode-priority
# guess (which would silently pick the South East London postcode instead, a
# completely different location). Other providers (octopus.energy's own
# region-letter scheme, energy-charts.info's own native bidding-zone codes)
# fall back to plain auto-detection.
PROVIDER_LOCATION_KIND: dict[type[BaseProvider], str] = {
    GBCarbonIntensityProvider: "gb_postcode",
    WattnetEuProvider: "wattnet_zone",
}


def detect_location(location: str) -> tuple[str, str]:
    """
    Work out whether `location` is a GB postcode or a wattnet.eu zone

    :return: (kind, canonical_location) where kind is "gb_postcode" or "wattnet_zone"
    :raises InvalidLocationError: if it matches neither scheme
    """
    try:
        return "gb_postcode", GBCarbonIntensityProvider().validate_location(location)
    except InvalidLocationError:
        pass
    try:
        return "wattnet_zone", WattnetEuProvider().validate_location(location)
    except InvalidLocationError:
        pass
    raise InvalidLocationError(
        f"{location}. Not a recognised GB postcode (for carbonintensity.org.uk/"
        "octopus.energy) or wattnet.eu zone code."
    )


def octopus_region_letter(postcode: str, timestamp: datetime) -> str:
    """
    Derive the Octopus region letter for a GB postcode

    Re-requests the same carbonintensity.org.uk URL the carbon intensity
    provider fetches (served from cache when already requested) purely to
    read its "regionid" field, which GBCarbonIntensityProvider.get_data()
    does not expose.
    """
    # Must align identically to GBCarbonIntensityProvider.get_data() for the
    # cache sharing described above to hit.
    dt = align_to_resolution(
        timestamp, GBCarbonIntensityProvider().get_temporal_resolution_minutes()
    )
    url = (
        "https://api.carbonintensity.org.uk/regional/intensity/"
        f"{dt.strftime('%Y-%m-%dT%H:%MZ')}/fw48h/postcode/{postcode}"
    )
    response: dict[str, Any] | None = fetch_url(url)
    assert response is not None, "No response from carbonintensity.org.uk"
    regionid = response["data"]["regionid"]
    letter = REGIONID_TO_OCTOPUS_LETTER.get(regionid)
    if letter is None:  # pragma: no cover - all postcode regionids are 1-14
        raise InvalidLocationError(
            f"Could not map NESO regionid {regionid} to an Octopus region"
        )
    return letter


def resolve_price_series(
    location: str,
    timestamp: datetime,
    provider_cls: type[BaseProvider] | None = None,
) -> Timeseries | None:
    """
    Get a day-ahead price series for a GB postcode or a wattnet.eu zone

    :param location: A GB postcode outward code or a wattnet.eu zone code
    :param timestamp: Timestamp from which to start forecast data retrieval
    :param provider_cls: The provider selected for the main forecast (via
        --api), if any. When it unambiguously implies one location kind (see
        PROVIDER_LOCATION_KIND), that kind is used instead of auto-detecting
        it, so an ambiguous code isn't silently reinterpreted as the other kind.
    :return: The price Timeseries, or None if this location has no price signal
    :raises InvalidLocationError: if `location` matches neither scheme at all
    """
    kind = PROVIDER_LOCATION_KIND.get(provider_cls) if provider_cls else None
    if kind == "gb_postcode":
        location = GBCarbonIntensityProvider().validate_location(location)
    elif kind == "wattnet_zone":
        location = WattnetEuProvider().validate_location(location)
    else:
        kind, location = detect_location(location)

    if kind == "gb_postcode":
        return OctopusAgilePriceProvider().get_data(
            timestamp, octopus_region_letter(location, timestamp), metric="price"
        )
    zone = WATTNET_TO_ENERGYCHARTS_ZONE.get(location)
    if zone is None:
        return None
    return EnergyChartsProvider().get_data(timestamp, zone, metric="price")


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
    price_values: list[PointEstimate], window_start: datetime, duration_minutes: int
) -> float:
    "Average price over one [window_start, window_start + duration_minutes] window"
    return WindowedForecast(
        price_values,
        duration_minutes,
        start=window_start,
        max_window_minutes=duration_minutes,
    )[0].value


def find_best_within_price_constraint(
    wf: WindowedForecast,
    price_values: list[PointEstimate],
    duration_minutes: int,
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
        price_now = price_at_window(price_values, now.start, duration_minutes)
        cap = price_now * (1 + max_price_increase_pct / 100)

    eligible = [
        estimate
        for estimate in wf
        if price_covers_window(price_values, estimate.start, estimate.end)
        and price_at_window(price_values, estimate.start, duration_minutes) <= cap
    ]
    if not eligible:
        raise PriceConstraintUnsatisfiableError(
            f"No candidate start time both falls within price data's forecast "
            f"horizon and satisfies the price constraint (cap={cap:.2f}); try "
            "relaxing --max-price/--max-price-increase-pct or removing it."
        )
    return min(eligible)

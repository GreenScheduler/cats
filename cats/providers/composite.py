"""
Unified composite provider

Combines signals from carbonintensity.org.uk, octopus.energy, wattnet.eu and
energy-charts.info, auto-detecting whether the given location is a GB
postcode or a wattnet.eu zone code and routing each requested metric to
whichever portal natively serves it for that kind of location, falling back
to wattnet.eu (with a logged note) for metrics no other portal has.
"""

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any, ClassVar


from ..exceptions import InvalidLocationError
from ..forecast import PointEstimate, Timeseries
from .base import BaseProvider, LocationGroup, align_to_resolution, fetch_url, provider
from .eu_energycharts import EU_RENEWABLES_COUNTRIES, EnergyChartsProvider
from .eu_wattnet import WattnetEuProvider
from .gb_octopus import OctopusAgilePriceProvider
from .gb_carbonintensity import GBCarbonIntensityProvider


def normalise(values: list[float]) -> list[float]:
    "Min-max normalise a list of values to the 0-1 range"
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def resolve_weights(
    requested: dict[str, float] | None, available_signals: Iterable[str]
) -> dict[str, float]:
    """
    Resolve which signals to combine and their normalised weights

    If `requested` is None or empty, every entry in `available_signals` is
    used, weighted equally. Otherwise `requested` is used as given (already
    restricted to available signals by the caller), letting the caller
    distinguish "signal not requested" from "signal requested but
    unavailable". Weights don't need to sum to 1 as given; they are
    normalised here so they always do.

    :raises ValueError: if the resulting weights sum to zero or less
    """
    available_signals = list(available_signals)
    weights = (
        {name: 1.0 for name in available_signals} if not requested else dict(requested)
    )
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Signal weights must sum to a positive number")
    return {name: w / total for name, w in weights.items()}


def combine_series(
    series_by_signal: dict[str, list[PointEstimate]], weights: dict[str, float]
) -> list[PointEstimate]:
    """
    Combine several named PointEstimate series into one normalised score

    Each series is independently min-max normalised to a 0-1 scale over the
    timestamps shared by *all* of them (real calendar timestamps are assumed
    to line up exactly across series, so this intersects rather than
    interpolates), then combined as a weighted sum using `weights` (which
    should already sum to 1, see resolve_weights()).

    :raises AssertionError: if the series share no common timestamps
    """
    by_time_per_signal = {
        name: {p.datetime: p.value for p in series}
        for name, series in series_by_signal.items()
    }
    shared_times = sorted(
        set.intersection(*(set(d) for d in by_time_per_signal.values()))
    )
    assert shared_times, "No overlapping timestamps between the requested signals"

    normalised_per_signal = {
        name: normalise([by_time[t] for t in shared_times])
        for name, by_time in by_time_per_signal.items()
    }

    return [
        PointEstimate(
            datetime=t,
            value=sum(
                weights[name] * normalised_per_signal[name][i] for name in weights
            ),
        )
        for i, t in enumerate(shared_times)
    ]


ALL_SIGNAL_NAMES: frozenset[str] = frozenset(
    {
        "carbon",
        "price",
        "renewables",
        "water",
        "water_stress",
        "environmental_score",
    }
)
# Signals excluded from the default (no --signal given) combination when the
# location is a GB postcode: unlike carbon/price/renewables (which come from
# carbonintensity.org.uk/octopus.energy, no authentication needed), these
# three only exist via wattnet.eu and need CATS_WATTNET_EMAIL/
# CATS_WATTNET_PASSWORD - a plain `--api composite` with a GB postcode and no
# --signal must keep working without wattnet credentials. When the location
# is a wattnet.eu zone instead, wattnet credentials are already required for
# `carbon`, so there is no such default-eligibility restriction there.
WATTNET_ONLY_SIGNALS: frozenset[str] = frozenset(
    {"water", "water_stress", "environmental_score"}
)

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

# wattnet.eu zone -> energy-charts.info /v2/signal country code, for the
# "renewables" signal when the location is a wattnet.eu zone. Derived with a
# simple rule (strip everything from the first "_" or trailing digit,
# lowercase) rather than a second static table, since wattnet zone codes
# already embed a plain ISO-ish country prefix in almost all cases. A
# handful of zones have no known country-level renewables-share equivalent
# and are excluded explicitly.
_NO_RENEWABLES_EQUIVALENT: frozenset[str] = frozenset({"GB", "NIE"})


def _wattnet_zone_to_renewables_country(zone: str) -> str | None:
    if zone in _NO_RENEWABLES_EQUIVALENT:
        return None
    country = zone.split("_")[0].rstrip("0123456789").lower()
    return country if country in EU_RENEWABLES_COUNTRIES else None


# (provider instance, metric on that provider, that provider's own location
# encoding, an optional note to log when this signal is used - e.g. because
# the location had to be translated to a different portal's zone/region).
SignalSpec = tuple[BaseProvider, str, str, "str | None"]


@provider("composite")
class CompositeProvider(BaseProvider):
    """
    Unified composite provider: picks the right portal per metric and location

    This can be used by passing the --api='composite' command line argument.
    Unlike the single-portal providers, the location it is given can be
    *either* a GB postcode outward code (e.g. 'OX1') *or* a wattnet.eu zone
    code (e.g. 'DE', 'IT_NORTH'); which kind is auto-detected by trying to
    validate it against carbonintensity.org.uk's postcode list first, falling
    back to wattnet.eu's zone list. A handful of codes are valid in both
    schemes (e.g. 'SE1'-'SE4' are both South East London postcodes and
    Swedish wattnet.eu price zones); the GB postcode interpretation always
    wins in that case. If you specifically want the wattnet.eu zone in such a
    clash, there is currently no way to force that interpretation.

    For each of six possible signals, the *native* portal for the detected
    location kind is used where one exists, falling back to wattnet.eu (with
    a logged warning noting the substitution) only when no other portal
    serves that metric at all:

    - carbon: carbonintensity.org.uk for a GB postcode (metric=carbon,
      postcode-granular, no authentication), wattnet.eu for a wattnet.eu
      zone (metric=carbon, needs CATS_WATTNET_EMAIL/CATS_WATTNET_PASSWORD).
    - price: octopus.energy for a GB postcode (region letter derived from
      the postcode automatically), energy-charts.info for a wattnet.eu zone
      (bidding zone looked up from the wattnet.eu zone, see
      WATTNET_TO_ENERGYCHARTS_ZONE) - not every wattnet.eu zone has an
      energy-charts.info price equivalent.
    - renewables: carbonintensity.org.uk for a GB postcode (metric=
      renewables, same API call as carbon), energy-charts.info for a
      wattnet.eu zone (country code derived from the wattnet.eu zone, see
      _wattnet_zone_to_renewables_country) - not every wattnet.eu zone has
      an energy-charts.info renewables equivalent.
    - water, water_stress, environmental_score: only wattnet.eu ever serves
      these. For a wattnet.eu zone location, that zone is used
      directly. For a GB postcode, wattnet.eu's single 'GB' zone is used
      instead (wattnet's GB coverage is not postcode-granular) and a
      logged warning notes the substitution; this needs wattnet.eu
      credentials even when the rest of the request (carbon/price/
      renewables from a GB postcode) would not.

    Which signals to combine, and their relative weight, is controlled with
    the repeatable --signal NAME=WEIGHT CLI flag, e.g.:

        --signal carbon=0.4 --signal price=0.3 --signal renewables=0.3
        --signal environmental_score=0.5 --signal price=0.5

    Weights don't need to sum to 1; they are normalised automatically.
    Requesting a signal that has no source at all for the detected location
    (e.g. 'price' for a wattnet.eu zone with no energy-charts.info mapping)
    raises a clear error. With no --signal given at all, every *available,
    no-extra-authentication* signal for that location is combined with equal
    weight: for a GB postcode that means carbon, price and renewables only
    (water/water_stress/environmental_score need explicit --signal, since
    they need wattnet.eu credentials the rest of a GB postcode request does
    not); for a wattnet.eu zone it means every signal
    that has a source at all for that zone (wattnet.eu credentials are
    already required there for carbon).

    Each signal's series is independently min-max normalised to a 0-1 scale
    over the overlapping forecast window fetched in this call, then combined
    as a weighted sum. Note the normalisation is relative to the data
    fetched in a given run, not to any fixed physical range, so the same
    absolute value can score differently on different days - a deliberate
    simplification for a first version of trade-off scheduling, not a
    physical calibration.
    """

    BASE_URL: ClassVar[str] = ""  # Unused: delegates entirely to the sub-providers

    @property
    def signals_requested(self) -> dict[str, float] | None:
        if self.api_data and "signals" in self.api_data:
            return self.api_data["signals"]
        return None

    @staticmethod
    def _detect_location(location: str | None) -> tuple[str, str]:
        """
        Work out whether `location` is a GB postcode or a wattnet.eu zone

        :return: (kind, canonical_location) where kind is "gb_postcode" or "wattnet_zone"
        :raises InvalidLocationError: if it matches neither scheme
        """
        if location is None:
            raise InvalidLocationError(
                "Must provide location (a GB postcode or a wattnet.eu zone code) "
                "for the composite provider"
            )
        try:
            return "gb_postcode", GBCarbonIntensityProvider().validate_location(
                location
            )
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

    def validate_location(self, location: str | None) -> str:
        return self._detect_location(location)[1]

    def _octopus_region_letter(self, postcode: str, timestamp: datetime) -> str:
        """
        Derive the Octopus region letter for a GB postcode

        Re-requests the same carbonintensity.org.uk URL the carbon intensity
        provider already fetched for this call (served from cache, so this
        costs no extra real HTTP request whenever carbon or renewables is
        also being requested) purely to read its "regionid" field, which is
        not otherwise exposed by GBCarbonIntensityProvider.get_data().
        """
        # Must align identically to GBCarbonIntensityProvider.get_data() for
        # the cache-sharing described above to actually hit.
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

    def _signal_specs(
        self, kind: str, location: str, timestamp: datetime
    ) -> dict[str, SignalSpec]:
        "Only entries that actually have a data source for this location/kind are included"
        wattnet = WattnetEuProvider()

        if kind == "gb_postcode":
            specs: dict[str, SignalSpec] = {
                "carbon": (GBCarbonIntensityProvider(), "carbon", location, None),
                "renewables": (
                    GBCarbonIntensityProvider(),
                    "renewables",
                    location,
                    None,
                ),
                "price": (
                    OctopusAgilePriceProvider(),
                    "price",
                    self._octopus_region_letter(location, timestamp),
                    None,
                ),
            }
            for wattnet_metric in WATTNET_ONLY_SIGNALS:
                specs[wattnet_metric] = (
                    wattnet,
                    wattnet_metric,
                    "GB",
                    f"{location!r} has no {wattnet_metric} data source; using "
                    "wattnet.eu's 'GB' zone instead (needs wattnet.eu credentials).",
                )
            return specs

        # kind == "wattnet_zone"
        specs = {
            "carbon": (wattnet, "carbon", location, None),
            "water": (wattnet, "water", location, None),
            "water_stress": (wattnet, "water_stress", location, None),
            "environmental_score": (wattnet, "environmental_score", location, None),
        }
        price_zone = WATTNET_TO_ENERGYCHARTS_ZONE.get(location)
        if price_zone is not None:
            specs["price"] = (EnergyChartsProvider(), "price", price_zone, None)
        renewables_country = _wattnet_zone_to_renewables_country(location)
        if renewables_country is not None:
            specs["renewables"] = (
                EnergyChartsProvider(),
                "renewables",
                renewables_country,
                None,
            )
        return specs

    def resolve_signal(
        self,
        name: str,
        location: str,
        timestamp: datetime,
        assume_kind: str | None = None,
    ) -> Timeseries | None:
        """
        Fetch one named composite signal for this location

        Independent of whichever combination (if any) is actually being
        requested via --signal - useful for a caller that only ever wants
        one specific signal (e.g. cats/pricing.py wanting just "price"),
        without needing to know about this class' internal signal registry.

        :param assume_kind: "gb_postcode" or "wattnet_zone" to skip
            auto-detecting the location kind and use this one directly.
            For a small number of codes valid under both schemes (e.g.
            'SE1'-'SE4'), auto-detection always prefers the GB postcode
            interpretation - which is wrong when the caller already knows,
            from a specific single-scheme provider having validated this
            same location string, that it is actually the other kind (e.g.
            `--api wattnet.eu --location SE1` unambiguously means the
            Swedish wattnet.eu zone, not the South East London postcode).
        :return: the signal's Timeseries, or None if this location has no
            data source for it at all
        :raises InvalidLocationError: if `location` matches neither the GB
            postcode nor the wattnet.eu zone scheme at all
        """
        if assume_kind == "gb_postcode":
            kind = "gb_postcode"
            canonical_location = GBCarbonIntensityProvider().validate_location(location)
        elif assume_kind == "wattnet_zone":
            kind = "wattnet_zone"
            canonical_location = WattnetEuProvider().validate_location(location)
        else:
            kind, canonical_location = self._detect_location(location)
        specs = self._signal_specs(kind, canonical_location, timestamp)
        if name not in specs:
            return None
        provider, metric, provider_location, note = specs[name]
        if note:
            logging.warning(note)
        return provider.get_data(timestamp, provider_location, metric=metric)

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        wattnet_zones = WattnetEuProvider().list_locations()[0].locations
        zones = {}
        for zone in sorted(wattnet_zones):
            extras = []
            if zone in WATTNET_TO_ENERGYCHARTS_ZONE:
                extras.append("price")
            if _wattnet_zone_to_renewables_country(zone):
                extras.append("renewables")
            zones[zone] = "+".join(extras)
        return [
            LocationGroup(
                "GB postcode outward codes (e.g. 'OX1')",
                {},
                "Same codes as carbonintensity.org.uk, see "
                "--list-locations carbonintensity.org.uk. Codes valid as both a "
                "postcode and a zone (e.g. 'SE1') are read as GB postcodes.",
            ),
            LocationGroup(
                "Wattnet zone codes",
                zones,
                "The value shown next to a zone lists its extra signals "
                "beyond carbon, water, water_stress and environmental_score.",
            ),
        ]

    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        # Location-independent nominal capability (used e.g. by
        # --list-providers, which has no location to detect a kind from):
        # the minimum across every provider/metric pair this composite could
        # ever use, regardless of which location kind is eventually given.
        return min(
            GBCarbonIntensityProvider().get_max_duration_minutes("carbon"),
            OctopusAgilePriceProvider().get_max_duration_minutes("price"),
            WattnetEuProvider().get_max_duration_minutes("carbon"),
            EnergyChartsProvider().get_max_duration_minutes("price"),
            EnergyChartsProvider().get_max_duration_minutes("renewables"),
        )

    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        # Nominal value for the GB postcode default combination (30 minute
        # settlement periods); a wattnet.eu zone location, or an explicit
        # wattnet.eu signal, uses 15 minute data instead. combine_series()
        # intersects by exact timestamp regardless of what this declares.
        return 30

    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """
        Get combined data across the requested signals for a GB postcode or wattnet.eu zone

        :param timestamp: Timestamp from which to start forecast data retrieval
        :param location: GB postcode outward code or wattnet.eu zone code
        :param metric: Optional, not supported by this provider
        :param headers: Optional, not used by this provider
        :return: Timeseries of normalised composite scores as PointEstimates
        """
        kind, canonical_location = self._detect_location(location)
        specs = self._signal_specs(kind, canonical_location, timestamp)
        requested = self.signals_requested

        if requested is not None:
            unknown_names = set(requested) - ALL_SIGNAL_NAMES
            if unknown_names:
                raise ValueError(
                    f"Unknown signal(s) {sorted(unknown_names)} for the composite "
                    f"provider; valid signal names: {sorted(ALL_SIGNAL_NAMES)}"
                )
            unavailable = set(requested) - set(specs)
            if unavailable:
                raise InvalidLocationError(
                    f"Signal(s) {sorted(unavailable)} have no data source for "
                    f"location {canonical_location!r} ({kind}); available here: "
                    f"{sorted(specs)}"
                )
            candidate_names = list(requested)
        else:
            default_eligible = (
                ALL_SIGNAL_NAMES - WATTNET_ONLY_SIGNALS
                if kind == "gb_postcode"
                else set(specs)
            )
            candidate_names = [n for n in specs if n in default_eligible]

        assert candidate_names, f"No signals available for location {location!r}"

        for name in candidate_names:
            note = specs[name][3]
            if note:
                logging.warning(note)

        # Signals can have different native resolutions (carbon/price/
        # renewables from a GB postcode use 30 minute periods; wattnet.eu
        # signals use 15). combine_series() intersects by exact timestamp,
        # so if each signal were requested starting from *its own*
        # resolution's boundary, the first timestamp they actually share
        # could land after `timestamp` even though each individual series
        # starts at or before it - aligning every request to the coarsest
        # resolution in play first ensures they all start from the same
        # shared boundary.
        coarsest_resolution = max(
            specs[name][0].get_temporal_resolution_minutes(specs[name][1])
            for name in candidate_names
        )
        aligned_timestamp = align_to_resolution(timestamp, coarsest_resolution)

        series_by_signal = {
            name: specs[name][0]
            .get_data(aligned_timestamp, specs[name][2], metric=specs[name][1])
            .values
            for name in candidate_names
        }
        weights = resolve_weights(requested, series_by_signal.keys())
        values = combine_series(series_by_signal, weights)

        label = ", ".join(f"{name}={w:.2f}" for name, w in sorted(weights.items()))
        return Timeseries(
            f"Composite score ({label})", values=values, unit="0-1, lower=better"
        )

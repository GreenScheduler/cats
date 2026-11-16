"US grid operators: carbon intensity from ERCOT and EIA-930 fuel mix"

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

from __future__ import annotations

import os
from bisect import bisect_right
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from typing import Any, ClassVar
from urllib.parse import urlencode

from ..exceptions import InvalidLocationError, ProviderAuthenticationError
from ..forecast import PointEstimate, Timeseries
from .base import (
    BaseProvider,
    LocationGroup,
    align_to_resolution,
    fetch_url,
    provider,
)

# Life-cycle emission factors in gCO2eq/kWh: medians from IPCC AR5 WG3
# Annex III, Table A.III.2 (Schlömer et al., 2014). Battery and other storage
# output is counted as zero here, since the emissions of the energy used to
# charge it were already counted when that energy was generated. Petroleum and
# unknown fuels share the gas figure, as AR5 gives no oil median.
EMISSION_FACTORS: dict[str, float] = {
    "coal": 820.0,
    "gas": 490.0,
    "other": 490.0,
    "biomass": 230.0,
    "geothermal": 38.0,
    "hydro": 24.0,
    "nuclear": 12.0,
    "solar": 48.0,
    "wind": 11.0,
    "storage": 0.0,
}

# Fuel names used on ERCOT's public fuel-mix dashboard
ERCOT_FUELS: dict[str, str] = {
    "Coal and Lignite": "coal",
    "Natural Gas": "gas",
    "Nuclear": "nuclear",
    "Solar": "solar",
    "Wind": "wind",
    "Hydro": "hydro",
    "Power Storage": "storage",
    "Other": "other",
}

# EIA-930 fuel type codes, as used by the EIA open data API (v2,
# electricity/rto/fuel-type-data). Codes not listed here count as "other".
EIA_FUELS: dict[str, str] = {
    "COL": "coal",
    "NG": "gas",
    "NUC": "nuclear",
    "OIL": "other",
    "OTH": "other",
    "UNK": "other",
    "WAT": "hydro",
    "GEO": "geothermal",
    "SUN": "solar",
    "SNB": "solar",
    "WND": "wind",
    "WNB": "wind",
    "BAT": "storage",
    "PS": "storage",
    "OES": "storage",
    "UES": "storage",
}

EIA_BALANCING_AUTHORITIES: frozenset[str] = frozenset(
    (files("cats") / "data" / "eia_balancing_authorities.txt").read_text().split()
)

# Forecast horizon offered by both providers: a persistence forecast repeats
# the last day, so it reaches 24 hours ahead. One step is dropped from the
# end, as for the other providers.
HORIZON = timedelta(hours=24)


def carbon_intensity(mix: Mapping[str, float], fuels: Mapping[str, str]) -> float:
    """
    Generation-weighted carbon intensity of one fuel mix, in gCO2eq/kWh

    :param mix: Generation (any power or energy unit) keyed by the source's
        own fuel names. Negative values, such as storage charging, are
        treated as zero generation.
    :param fuels: Map from the source's fuel names to keys of EMISSION_FACTORS.
        Fuel names missing from the map count as "other".
    :raises ValueError: if the mix has no positive generation
    """
    total = 0.0
    weighted = 0.0
    for fuel, generation in mix.items():
        if generation is None or generation <= 0:
            continue
        total += generation
        weighted += generation * EMISSION_FACTORS[fuels.get(fuel, "other")]
    if total <= 0:
        raise ValueError("Fuel mix has no positive generation")
    return weighted / total


def persistence_forecast(
    history: Iterable[PointEstimate],
    start: datetime,
    step: timedelta,
    horizon: timedelta = HORIZON,
    days: int = 1,
) -> list[PointEstimate]:
    """
    Forecast by repeating recent days

    The value at each future time t is the mean of the observed values at
    t - 1 day, t - 2 days, ... using the `days` most recent of those that
    exist in `history`. Observations are matched to the nearest earlier
    point within one `step`. This is the "same time yesterday" forecast
    when days=1, and needs no data beyond what the grid operator has
    already published.

    :param history: Observed values, any order
    :param start: First forecast time (aligned to `step`)
    :param step: Spacing of the forecast points
    :param horizon: How far ahead to forecast
    :param days: How many past days to average
    :return: Forecast points from `start` up to `start + horizon`, sorted;
        times with no matching past observation are left out
    """
    observed = sorted(history, key=lambda p: p.datetime)
    if not observed:
        return []
    times = [p.datetime for p in observed]

    def value_at(when: datetime) -> float | None:
        # The latest observation in (when - step, when]: sources may stamp a
        # few seconds or minutes into the interval (ERCOT's dashboard does)
        i = bisect_right(times, when) - 1
        if i >= 0 and times[i] > when - step:
            return observed[i].value
        return None

    points: list[PointEstimate] = []
    t = start
    while t <= start + horizon:
        values: list[float] = []
        lag = timedelta(days=1)
        while len(values) < days and t - lag >= times[0]:
            value = value_at(t - lag)
            if value is not None:
                values.append(value)
            lag += timedelta(days=1)
        if values:
            points.append(PointEstimate(datetime=t, value=sum(values) / len(values)))
        t += step
    return points


@provider("ercot.com")
class ERCOTProvider(BaseProvider):
    """
    Carbon intensity for the ERCOT (Texas) grid from ERCOT's public fuel mix

    This can be used by passing the --api='ercot.com' command line argument
    with --location=ERCOT. No authentication is required. ERCOT's public
    fuel-mix dashboard reports generation by fuel every 5 minutes for the
    current and the previous day, a few minutes behind real time. It does
    not publish a carbon intensity forecast, so this provider converts the
    observed fuel mix to carbon intensity with IPCC AR5 life-cycle factors
    (EMISSION_FACTORS) and forecasts the next 24 hours as the same time on
    the previous day (a persistence forecast). This is a simple forecast:
    it does not anticipate tomorrow's wind or a cold front.

    ERCOT's website terms allow its raw public data to be used in analyses.
    """

    BASE_URL: ClassVar[str] = "https://www.ercot.com"
    PATH: ClassVar[str] = "/api/1/services/read/dashboards/fuel-mix.json"
    LOCATIONS: ClassVar[dict[str, str]] = {
        "ERCOT": "Electric Reliability Council of Texas"
    }

    def validate_location(self, location: str | None) -> str:
        if location is None or location.upper() not in self.LOCATIONS:
            raise InvalidLocationError(
                f"{location}. The ercot.com provider only covers --location=ERCOT"
            )
        return location.upper()

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        return [LocationGroup("Grid operator", dict(self.LOCATIONS))]

    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        return (
            int(HORIZON.total_seconds() // 60) - self.get_temporal_resolution_minutes()
        )

    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        return 5

    def observed(self, response: Mapping[str, Any]) -> list[PointEstimate]:
        "Carbon intensity of every 5-minute fuel mix in a dashboard response"
        points: list[PointEstimate] = []
        for day in response["data"].values():
            for stamp, mix in day.items():
                # "Power Storage" is the net of the charging and discharging
                # entries that follow it, so those two are not counted again
                generation = {
                    fuel: value["gen"]
                    for fuel, value in mix.items()
                    if fuel in ERCOT_FUELS
                }
                try:
                    value = carbon_intensity(generation, ERCOT_FUELS)
                except ValueError:
                    continue
                when = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S%z")
                points.append(
                    PointEstimate(datetime=when.astimezone(timezone.utc), value=value)
                )
        return sorted(points, key=lambda p: p.datetime)

    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """
        Get ERCOT's recent fuel mix and turn it into a 24 hour forecast

        :param timestamp: Time from which to start the forecast
        :param location: Must be "ERCOT"
        :param metric: Not used, only carbon intensity is served
        :param headers: Not used by this provider
        """
        self.validate_location(location)
        step = timedelta(minutes=self.get_temporal_resolution_minutes())
        start = align_to_resolution(timestamp, self.get_temporal_resolution_minutes())
        # The aligned time in the query makes each 5-minute request a new
        # cache entry; ERCOT ignores the parameter.
        url = f"{self.base_url}{self.PATH}?{urlencode({'t': start.strftime('%Y-%m-%dT%H:%MZ')})}"
        response = fetch_url(url)
        assert response and response.get("data"), (
            "Empty response from ERCOT fuel mix request"
        )
        values = persistence_forecast(self.observed(response), start, step)
        return Timeseries("Carbon intensity", values=values, unit="gCO2eq/kWh")


@provider("eia.gov")
class EIAProvider(BaseProvider):
    """
    Carbon intensity for US balancing authorities from EIA-930 hourly fuel mix

    This can be used by passing the --api='eia.gov' command line argument
    with --location set to an EIA balancing authority code, e.g. 'ERCO'
    (ERCOT), 'CISO' (California ISO), 'PJM', 'MISO'. It reads the hourly
    net generation by fuel that balancing authorities report to the U.S.
    Energy Information Administration (form EIA-930) and converts it to
    carbon intensity with IPCC AR5 life-cycle factors (EMISSION_FACTORS).
    EIA-930 data are observations, not forecasts, so this provider forecasts
    the next 24 hours as the same hour on the previous day (a persistence
    forecast). Balancing authorities report with a delay of an hour or more,
    so the forecast uses the most recent day that has been published.

    The EIA open data API needs a free API key, registered at
    https://www.eia.gov/opendata/. Set it in the CATS_EIA_API_KEY
    environment variable. EIA data are in the public domain.
    """

    BASE_URL: ClassVar[str] = "https://api.eia.gov"
    PATH: ClassVar[str] = "/v2/electricity/rto/fuel-type-data/data/"
    # Days of history to request: enough for the persistence forecast even
    # when the newest day is not yet published.
    HISTORY: ClassVar[timedelta] = timedelta(days=3)

    def validate_location(self, location: str | None) -> str:
        if location is None or location.upper() not in EIA_BALANCING_AUTHORITIES:
            raise InvalidLocationError(
                f"{location}. The eia.gov provider needs an EIA-930 balancing "
                "authority code, e.g. 'ERCO', 'CISO', 'PJM'. See "
                "cats/data/eia_balancing_authorities.txt for the full list."
            )
        return location.upper()

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        return [
            LocationGroup(
                "EIA-930 balancing authorities",
                dict.fromkeys(sorted(EIA_BALANCING_AUTHORITIES), ""),
                "e.g. 'ERCO' (Texas), 'CISO' (California), 'PJM', 'MISO'.",
            )
        ]

    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        return (
            int(HORIZON.total_seconds() // 60) - self.get_temporal_resolution_minutes()
        )

    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        return 60

    @staticmethod
    def observed(response: Mapping[str, Any]) -> list[PointEstimate]:
        """
        Hourly carbon intensity from an API response

        EIA-930 periods are UTC and mark the end of each hour, so a value for
        period "2025-01-01T05" covers 04:00-05:00 UTC and is placed at 04:00.
        """
        mixes: dict[datetime, dict[str, float]] = {}
        for row in response["response"]["data"]:
            if row.get("value") is None:
                continue
            end = datetime.strptime(row["period"], "%Y-%m-%dT%H").replace(
                tzinfo=timezone.utc
            )
            mix = mixes.setdefault(end - timedelta(hours=1), {})
            mix[row["fueltype"]] = mix.get(row["fueltype"], 0.0) + float(row["value"])
        points: list[PointEstimate] = []
        for start, mix in mixes.items():
            try:
                points.append(
                    PointEstimate(
                        datetime=start, value=carbon_intensity(mix, EIA_FUELS)
                    )
                )
            except ValueError:
                continue
        return sorted(points, key=lambda p: p.datetime)

    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """
        Get recent EIA-930 fuel mix and turn it into a 24 hour forecast

        :param timestamp: Time from which to start the forecast
        :param location: EIA-930 balancing authority code
        :param metric: Not used, only carbon intensity is served
        :param headers: Not used by this provider
        """
        location = self.validate_location(location)
        api_key = os.environ.get("CATS_EIA_API_KEY")
        if not api_key:
            raise ProviderAuthenticationError(
                "The eia.gov provider needs a free EIA API key in the "
                "CATS_EIA_API_KEY environment variable, see https://www.eia.gov/opendata/"
            )
        start = align_to_resolution(timestamp, 60)
        query = {
            "api_key": api_key,
            "frequency": "hourly",
            "data[0]": "value",
            "facets[respondent][]": location,
            "start": (start - self.HISTORY).strftime("%Y-%m-%dT%H"),
            "end": start.strftime("%Y-%m-%dT%H"),
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": "5000",
        }
        response = fetch_url(f"{self.base_url}{self.PATH}?{urlencode(query)}")
        assert response and response.get("response", {}).get("data"), (
            "Empty response from EIA fuel type request"
        )
        values = persistence_forecast(
            self.observed(response), start, timedelta(hours=1)
        )
        return Timeseries("Carbon intensity", values=values, unit="gCO2eq/kWh")

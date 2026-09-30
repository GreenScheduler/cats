"UK Carbon Intensity API"

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

from datetime import datetime
from importlib.resources import files
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from ..exceptions import InvalidLocationError
from ..forecast import PointEstimate, Timeseries
from .base import (
    BaseProvider,
    LocationGroup,
    align_to_resolution,
    fetch_url,
    provider,
    resolve_metric,
)

INVALID_LOCATION_MESSAGE = (
    "{location}. UKCarbonIntensityProvider only supports UK postcodes, "
    + "specified as the outward code, for example 'OX1' for postcode 'OX1 3QD'"
)
# This file is generated using scripts/uk_outcodes.py:
#     python3 scripts/uk_outcodes.py <ONS postcode file> -o cats/data/uk_outcodes.txt
# ONS data:
# https://geoportal.statistics.gov.uk/datasets/6fff67d204fd4f339591ed667a6e3642/about
UK_OUTCODES: set[str] = set(
    (files("cats") / "data" / "uk_outcodes.txt").read_text().split()
)

# Fuel types counted as renewable in the API's own "generationmix" breakdown,
# matching NESO's own classification (their public dashboard sums exactly
# these four categories as "renewable"). The remaining fuel types reported
# (coal, gas, nuclear, imports, other) are not counted: nuclear is
# low-carbon but not renewable, and imports/other are of unknown or mixed
# origin.
RENEWABLE_FUELS: frozenset[str] = frozenset({"biomass", "hydro", "solar", "wind"})


@provider("carbonintensity.org.uk")
class UKCarbonIntensityProvider(BaseProvider):
    """
    Provider for the National Energy System Operator's carbonintensity.org.uk API

    The service covers most of Great Britain with the location specified using a the first part
    of a UK postcode. This relates to one of 14 areas forming the GB grid which each have their own
    forecast. Data has 30 minute resolution and extends 2 days into the future. No authentication
    is needed.

    Supports two metrics from the same underlying API response (selected with --metric):

    - carbon (default): carbon intensity of the GB grid, in gCO2eq/kWh.
    - renewables: non-renewable generation share (100 minus the sum of the biomass, hydro, solar
      and wind percentages in the API's own "generationmix" breakdown, see RENEWABLE_FUELS). Lower
      is still "better" here, matching CATS' minimum-average-window scheduler, whereas raw
      renewable share would need "higher is better" (which the scheduler does not support). Not
      compatible with --footprint, which only applies when forecast.metric == "Carbon intensity".

    Both metrics come from a single API call (the response already includes both "intensity" and
    "generationmix" for every period), so requesting both in the same run - e.g. via the composite
    provider - costs only one real HTTP request; the second is served from the shared fetch_url() cache.
    """

    BASE_URL: ClassVar[str] = "https://api.carbonintensity.org.uk"
    SUPPORTED_METRICS: ClassVar[frozenset[str]] = frozenset({"carbon", "renewables"})
    DEFAULT_METRIC: ClassVar[str] = "carbon"

    def validate_location(self, location: str | None) -> str:
        if location is None:
            raise InvalidLocationError(
                "Must provide location for UK Carbon Intensity provider"
            )
        location = location.upper()
        # UK postcodes have two components, an out-code and in-code, e.g. OX1 3QD
        # The API only requires the outcode
        location = location.split()[0]
        if location in UK_OUTCODES:
            return location
        raise InvalidLocationError(INVALID_LOCATION_MESSAGE.format(location=location))

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return [
            LocationGroup(
                "UK postcode outward codes (e.g. 'OX1' for postcode 'OX1 3QD')",
                dict.fromkeys(sorted(UK_OUTCODES), ""),
            )
        ]

    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return 2820

    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return 30

    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        if location is None:
            raise InvalidLocationError(
                "Location must be supplied for UK Carbon Intensity API"
            )
        location = self.validate_location(location)
        metric = resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        dt = align_to_resolution(timestamp, self.get_temporal_resolution_minutes())
        url = (
            f"{self.base_url}/regional/intensity/"
            f"{dt.strftime('%Y-%m-%dT%H:%MZ')}"
            "/fw48h/postcode/"
            f"{location}"
        )

        response: dict[str, Any] | None = fetch_url(url)
        if response is None or "postcode" in response.get("error", {}).get(
            "message", {}
        ):
            raise InvalidLocationError(
                INVALID_LOCATION_MESSAGE.format(location=location)
            )

        # The "Z" at the end of the format string indicates UTC,
        # however, strptime does not know how to parse this, so we
        # need to add tzinfo data.
        datefmt = "%Y-%m-%dT%H:%MZ"
        utc = ZoneInfo("UTC")
        if metric == "carbon":
            values = [
                PointEstimate(
                    datetime=datetime.strptime(d["from"], datefmt).replace(tzinfo=utc),
                    value=d["intensity"]["forecast"],
                )
                for d in response["data"]["data"]
            ]
            return Timeseries("Carbon intensity", values=values, unit="gCO2eq/kWh")
        else:  # metric == "renewables"
            values = [
                PointEstimate(
                    datetime=datetime.strptime(d["from"], datefmt).replace(tzinfo=utc),
                    value=100
                    - sum(
                        gm["perc"]
                        for gm in d["generationmix"]
                        if gm["fuel"] in RENEWABLE_FUELS
                    ),
                )
                for d in response["data"]["data"]
            ]
            return Timeseries("Non-renewable share", values=values, unit="%")

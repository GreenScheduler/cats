"Octopus Energy Agile tariff API"

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

from datetime import datetime, timedelta
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

# The 14 GB electricity distribution regions, identified by letter, as used
# by both Octopus Energy tariffs and carbonintensity.org.uk (whose provider
# maps UK postcodes onto the same 14 areas).
REGION_NAMES: dict[str, str] = {
    "A": "East England",
    "B": "East Midlands",
    "C": "London",
    "D": "Merseyside & Northern Wales",
    "E": "West Midlands",
    "F": "North East England",
    "G": "North West England",
    "H": "South England",
    "J": "South East England",
    "K": "South Wales",
    "L": "South West England",
    "M": "Yorkshire",
    "N": "South Scotland",
    "P": "North Scotland",
}
VALID_REGIONS: set[str] = set(REGION_NAMES)
INVALID_LOCATION_MESSAGE = (
    "{location}. OctopusAgilePriceProvider only supports GB electricity "
    "distribution region letters, e.g. 'C' for London. Valid regions: "
    + ", ".join(f"{letter} ({name})" for letter, name in sorted(REGION_NAMES.items()))
)


@provider("octopus.energy")
class OctopusAgilePriceProvider(BaseProvider):
    """
    Provider for the Octopus Energy Agile tariff API

    This can be used by passing the --api='octopus.energy' command line
    argument. Agile Octopus is a retail electricity tariff whose half-hourly
    unit rate tracks the GB day-ahead wholesale price plus a margin, published
    in advance (typically from around 16:00 UK time for the following day).
    Great Britain is split into 14 electricity distribution regions, matching
    the areas used by carbonintensity.org.uk, identified by a single letter:

    A East England        F North East England    K South Wales
    B East Midlands       G North West England     L South West England
    C London              H South England          M Yorkshire
    D Merseyside & N Wales J South East England     N South Scotland
    E West Midlands                                 P North Scotland

    Data has 30 minute resolution. No authentication is required.

    This is the GB counterpart to the energy-charts.info price provider, which
    does not cover Great Britain (GB is outside the EU single day-ahead market
    coupling that energy-charts.info data is sourced from).

    Note this is a *cost* metric (price in GBP/MWh, excluding VAT), not a
    carbon intensity metric. Lower price is still "better" for scheduling
    purposes, so it works unmodified with CATS' minimum-average-window
    scheduler, but it is not compatible with --footprint, which only applies
    when forecast.metric == "Carbon intensity". Prices are in GBP, not EUR, so
    they are not directly comparable to the energy-charts.info provider
    without accounting for the exchange rate. As a retail tariff rate rather
    than a wholesale market clearing price, absolute values include Octopus'
    margin and are not identical to (though they closely track) the
    underlying GB wholesale day-ahead price.
    """

    BASE_URL: ClassVar[str] = "https://api.octopus.energy/v1"
    SUPPORTED_METRICS: ClassVar[frozenset[str]] = frozenset({"price"})
    DEFAULT_METRIC: ClassVar[str] = "price"

    def validate_location(self, location: str | None) -> str:
        if location is None:
            raise InvalidLocationError(
                "Must provide location (GB region letter) for Octopus Agile provider"
            )
        location = location.upper()
        if location in VALID_REGIONS:
            return location
        raise InvalidLocationError(INVALID_LOCATION_MESSAGE.format(location=location))

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return [
            LocationGroup(
                "GB electricity distribution region letters",
                dict(sorted(REGION_NAMES.items())),
            )
        ]

    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        # Nominal "today + tomorrow" day-ahead window, lop off one 30 min
        # settlement period from the end, matching the convention used by
        # uk_carbonintensity.py. Actual data availability can be less than
        # this until tomorrow's Agile rates are published, typically around
        # 16:00 UK time.
        return 2820

    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return 30

    def _current_agile_product_code(self) -> str:
        """
        Find the code of the currently active Octopus Energy Agile product

        The Agile product code is versioned (e.g. "AGILE-24-10-01") and Octopus
        periodically releases a new version, so rather than hardcoding a code
        that would eventually go stale, look up whichever Octopus-brand Agile
        import product is currently active (available_to is null).
        """
        response: dict[str, Any] | None = fetch_url(f"{self.base_url}/products/")
        assert response is not None, "No response from Octopus products request"
        for result in response.get("results", []):
            code = result.get("code", "")
            if (
                code.startswith("AGILE-")
                and "OUTGOING" not in code
                and result.get("brand") == "OCTOPUS_ENERGY"
                and result.get("available_to") is None
            ):
                return code
        raise InvalidLocationError(
            "Could not find an active Octopus Agile product"
        )  # pragma: no cover

    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """
        Get data from the Octopus Agile tariff API

        This method creates a URL for the request in a format that supports
        caching, gets the data, and converts it into CATS internal data format.

        :param timestamp: Timestamp from which to start forecast data retrieval
        :param location: GB electricity distribution region letter (e.g. 'C')
        :param metric: Optional, not supported by this provider
        :param headers: Optional, not used by this provider
        :return: Timeseries as a list of PointEstimate classes
        """
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        location = self.validate_location(location)
        product_code = self._current_agile_product_code()
        tariff_code = f"E-1R-{product_code}-{location}"

        start_time = align_to_resolution(
            timestamp, self.get_temporal_resolution_minutes()
        )
        end_time = start_time + timedelta(minutes=self.get_max_duration_minutes())

        url = (
            f"{self.base_url}/products/{product_code}/electricity-tariffs/"
            f"{tariff_code}/standard-unit-rates/?"
            f"period_from={start_time.strftime('%Y-%m-%dT%H:%MZ')}&"
            f"period_to={end_time.strftime('%Y-%m-%dT%H:%MZ')}"
        )

        response: dict[str, Any] | None = fetch_url(url)
        # location has already been validated against the static region list
        # above, so a missing/empty "results" field indicates a genuine
        # upstream/availability problem rather than a bad location.
        assert response is not None, "No response from Octopus Agile request"
        assert response.get("results"), "Empty response from Octopus Agile request"

        # The "Z" at the end of the format string indicates UTC, however,
        # strptime does not know how to parse this, so we need to add tzinfo
        # data, matching the pattern used by uk_carbonintensity.py.
        datefmt = "%Y-%m-%dT%H:%M:%SZ"
        utc = ZoneInfo("UTC")
        values = [
            PointEstimate(
                datetime=datetime.strptime(d["valid_from"], datefmt).replace(
                    tzinfo=utc
                ),
                # Octopus reports pence/kWh excl. VAT; GBP/MWh = pence/kWh * 10
                value=d["value_exc_vat"] * 10,
            )
            for d in response["results"]
        ]
        # The API returns results in descending (most recent first) order,
        # unlike the other bundled providers, but downstream scheduling logic
        # assumes an ascending timeseries.
        values.sort(key=lambda p: p.datetime)
        return Timeseries("Day-ahead electricity price", values=values, unit="GBP/MWh")

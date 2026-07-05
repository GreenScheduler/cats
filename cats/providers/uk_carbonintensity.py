"UK Carbon Intensity API"

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

from datetime import datetime
from importlib.resources import files
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from typing_extensions import override

from ..exceptions import InvalidLocationError
from ..forecast import PointEstimate, Timeseries
from .base import BaseProvider, fetch_url, provider

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


@provider("carbonintensity.org.uk")
class UKCarbonIntensityProvider(BaseProvider):
    BASE_URL: ClassVar[str] = "https://api.carbonintensity.org.uk"

    @override
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

    @override
    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        return 2820

    @override
    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        return 30

    @override
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
        patch_minute = 31 if timestamp.minute > 30 else 1
        dt = timestamp.replace(minute=patch_minute, second=0, microsecond=0)
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
        values = [
            PointEstimate(
                datetime=datetime.strptime(d["from"], datefmt).replace(tzinfo=utc),
                value=d["intensity"]["forecast"],
            )
            for d in response["data"]["data"]
        ]
        return Timeseries("Carbon intensity", values=values, unit="gCO2eq/kWh")

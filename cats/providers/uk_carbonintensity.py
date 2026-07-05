"UK Carbon Intensity API"

# pyright: reportUnknownArgumentType=none, reportUnknownVariableType=none, reportAny=none

import re
from datetime import datetime
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from typing_extensions import override

from ..exceptions import InvalidLocationError
from ..forecast import PointEstimate, Timeseries
from .base import BaseProvider, fetch_url, provider

UK_POSTCODE_REGEX = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?")
INVALID_LOCATION_MESSAGE = (
    "{location}. UKCarbonIntensityProvider only supports UK postcodes, "
    + "specified as the outward code, for example 'OX1' for postcode 'OX1 3QD'"
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
        match = UK_POSTCODE_REGEX.match(location)
        if match is not None:
            return match.group(0)
        else:
            raise InvalidLocationError(
                INVALID_LOCATION_MESSAGE.format(location=location)
            )

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

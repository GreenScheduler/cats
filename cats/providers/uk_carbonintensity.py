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


@provider("carbonintensity.org.uk")
class UKCarbonIntensityProvider(BaseProvider):
    MAX_DURATION_MINUTES: ClassVar[int] = 2820

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
            raise InvalidLocationError(f"Invalid UK postcode supplied: {location}")

    @override
    def get_data(
        self,
        timestamp: datetime,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        patch_minute = 31 if timestamp.minute > 30 else 1
        dt = timestamp.replace(minute=patch_minute, second=0, microsecond=0)
        url = (
            "https://api.carbonintensity.org.uk/regional/intensity/"
            f"{dt.strftime('%Y-%m-%dT%H:%MZ')}"
            "/fw48h/postcode/"
            f"{self.location}"
        )

        response: dict[str, Any] | None = fetch_url(url)
        if response is None or "postcode" in response.get("error", {}).get(
            "message", {}
        ):
            raise InvalidLocationError("Invalid UK postcode: {postcode}")

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

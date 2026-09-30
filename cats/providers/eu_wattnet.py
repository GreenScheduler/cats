"Wattnet API"

import datetime
import os
from importlib.resources import files
from typing import ClassVar
from zoneinfo import ZoneInfo

import requests
from typing_extensions import override

from ..exceptions import InvalidLocationError, ProviderAuthenticationError
from ..forecast import PointEstimate, Timeseries
from ..version import user_agent
from .base import BaseProvider, align_to_resolution, fetch_url, provider, resolve_metric

# Generated from Wattnet API zones get request piped into jq | grep "zones"
# and cleaned up.
WATTNET_ZONES: set[str] = set(
    (files("cats") / "data" / "wattnet_zones.txt").read_text().split()
)

# Each metric maps to a different wattnet.eu endpoint (not a shared endpoint
# with more parameters), confirmed against the live API: /v1/footprints
# takes footprint_type=carbon|water, /v1/impacts only accepts
# impact_type=water, and /v1/environmental-score takes no parameter at all.
# All three response shapes share the same series/values structure, so
# get_data() below parses them identically regardless of endpoint.
METRIC_ENDPOINTS: dict[str, tuple[str, str]] = {
    "carbon": ("/v1/footprints", "footprint_type=carbon&"),
    "water": ("/v1/footprints", "footprint_type=water&"),
    "water_stress": ("/v1/impacts", "impact_type=water&"),
    "environmental_score": ("/v1/environmental-score", ""),
}
METRIC_NAMES: dict[str, str] = {
    "carbon": "Carbon intensity",
    "water": "Water footprint",
    "water_stress": "Water stress",
    # Inverted (100 - raw score), see get_data() below.
    "environmental_score": "Non-environmental score",
}


@provider("wattnet.eu")
class WattnetEuProvider(BaseProvider):
    """
    Experimental provider for the wattnet.eu project API

    This can be used by passing the --api='wattnet.eu' command line
    argument. The service covers most of Europe with the location specified
    using a short code that typically refers to a single country. Data has
    15 minute resolution and extends 72 hours into the future.

    Supports four metrics from three separate wattnet.eu endpoints
    (selected with --metric; confirmed live against the real API):

    - carbon (default): carbon intensity, life-cycle scope, in gCO2/kWh
      (unit read from the API response, not hardcoded).
    - water: water footprint, life-cycle scope, in l/kWh.
    - water_stress: water-stress-weighted water footprint, operational
      scope, in stress-l/kWh - accounts for local water scarcity, unlike
      water's plain volume figure.
    - environmental_score: wattnet's own composite environmental score,
      operational scope. The API gives no unit; higher is better (the
      usual convention for "scores"), so this provider inverts it
      (100 - score) so that lower is still "better" for CATS'
      minimum-average-window scheduler, consistent with every other
      metric in CATS.

    Only carbon keeps the Timeseries.metric name "Carbon intensity", so
    that --footprint (which checks forecast.metric == "Carbon intensity" in
    cli.py) keeps working; the other three metrics are not compatible with
    --footprint.

    Note that this provider is an experimental service and requires authentication.
    You will need to arrange a user name and password to be set outside of CATS
    and specify these in two environment variables: CATS_WATTNET_EMAIL and
    CATS_WATTNET_PASSWORD. CATS arranges to use these to obtain a short term
    access token. See https://docs.wattnet.eu for details on registering for an
    account and obtaining these credentials.
    """

    BASE_URL: ClassVar[str] = "https://api.wattnet.eu"
    SUPPORTED_METRICS: ClassVar[frozenset[str]] = frozenset(METRIC_ENDPOINTS)
    DEFAULT_METRIC: ClassVar[str] = "carbon"

    def update_authorization_token(self) -> None:
        """
        Update the short-lived access token for the wattnet API

        To access the watnet API an access token is needed. This can
        be obtained using an API call with a pre-authorized email address
        and password. The access token is stored in the api_key attribute.
        This method gets a new token (with a the email address and password
        extracted from environment variables) and updates the api_key attribute.

        NB: the HTTP calls in this method are not cached.
        """
        if self.api_data is None:
            self.api_data = {}
        email = os.environ.get("CATS_WATTNET_EMAIL")
        password = os.environ.get("CATS_WATTNET_PASSWORD")
        if (email is None) or (password is None):
            raise ProviderAuthenticationError(
                "CATS_WATTNET_EMAIL and CATS_WATTNET_PASSWORD "
                "environment variables must be set for the wattnet provider"
            )
        data = {"email": email, "password": password}
        headers = {"Content-Type": "application/json"}
        headers.update(user_agent)
        url = f"{self.base_url}/token-request/get_token"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            raise ProviderAuthenticationError(
                f"Wattnet token request failed with status {response.status_code}"
            )
        result = response.json()
        self.api_data["access_token"] = result["access_token"]
        self.api_data["expires_at"] = datetime.datetime.fromisoformat(
            result["expires_at"]
        )

    @override
    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return 4305  # Looks like 72 hours of data, lop off 15 mins from the end

    @override
    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        return 15  # Looks like 15 min resolution

    @override
    def get_data(
        self,
        timestamp: datetime.datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """
        Get data from the wattnet API

        This method creates a URL for the request in a format that supports
        caching, deals with the authentication (if needed), gets the data,
        and converts it into CATS internal data format.

        :param timestamp: Timestamp from which to start forecast data retrieval
        :param location: Location for which to start forecast data retrieval
        :param metric: One of carbon, water, water_stress, environmental_score
        :param headers: Optional, if specified, passes additional headers
        :return: Timeseries as a list of PointEstimate classes
        """
        location = self.validate_location(location)
        metric = resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)
        start_time = align_to_resolution(
            timestamp, self.get_temporal_resolution_minutes(metric)
        )
        end_time = start_time + datetime.timedelta(
            minutes=self.get_max_duration_minutes(metric)
        )

        # Build URL. Note that because we use timezone aware datetime object
        # (and force them into UTC) .isoformat() adds +00:00 to the end of
        # the times in the URL. This breaks things. Instead we use strftime
        # to build the URL and check that the timezone offset is 0 as needed
        assert start_time.utcoffset() == datetime.timedelta(0), (
            "Internal timezone error"
        )
        path, query_params = METRIC_ENDPOINTS[metric]
        url = (
            f"{self.base_url}{path}?"
            f"{query_params}"
            f"zone={location}&"
            f"start={start_time.strftime('%Y-%m-%dT%H:%M:%S')}&"
            f"end={end_time.strftime('%Y-%m-%dT%H:%M:%S')}"
        )

        # Setup authentication if this has not been done. expires_at is
        # timezone-aware (parsed from the API's ISO-formatted response), so
        # compare against an aware "now" rather than datetime.now()'s naive
        # local time to avoid a TypeError.
        now = datetime.datetime.now(datetime.timezone.utc)
        if (self.api_data is None) or (self.api_data["expires_at"] < now):
            self.update_authorization_token()
        now = datetime.datetime.now(datetime.timezone.utc)
        if (self.api_data is None) or (self.api_data["expires_at"] < now):
            raise ProviderAuthenticationError("Unexpected Wattnet authentication error")
        headers = {"Authorization": f"Bearer {self.api_data['access_token']}"}

        # Get the data
        response: list | None = fetch_url(url, headers=headers)

        # Invalid responses may return empty lists. We've done the useful
        # validation already, so just raise an assertion error.
        assert response is not None, (
            "No response from Wattnet request"
        )  # To catch failed for typing
        assert response, "Empty response from Wattnet request"  # empty list is Falsey

        # The "Z" at the end of the format string indicates UTC,
        # however, strptime does not know how to parse this, so we
        # need to add tzinfo data. All three endpoints share the same
        # series/values structure regardless of metric.
        datefmt = "%Y-%m-%dT%H:%M:%SZ"
        utc = ZoneInfo("UTC")
        raw_values = response[0]["series"][0]["values"]

        if metric == "environmental_score":
            values = [
                PointEstimate(
                    datetime=datetime.datetime.strptime(t, datefmt).replace(tzinfo=utc),
                    value=100 - v,
                )
                for t, v in raw_values
            ]
            return Timeseries(
                METRIC_NAMES[metric],
                values=values,
                unit="score (0-100, lower=better)",
            )

        unit = response[0].get("unit", "")
        values = [
            PointEstimate(
                datetime=datetime.datetime.strptime(t, datefmt).replace(tzinfo=utc),
                value=v,
            )
            for t, v in raw_values
        ]
        return Timeseries(METRIC_NAMES[metric], values=values, unit=unit)

    @override
    def validate_location(self, location: str | None) -> str:
        """
        Check that Wattnet location data matches the list of supported locations

        Wattnet uses a set of zones with short names such as 'GB', 'IT_CALABRIA',
        or 'SE1'. A full list can be found in data/wattnet_zones.txt.

        raises: InvalidLocationError if the location is not provided or matched
        """
        if location is None:
            raise InvalidLocationError("Must provide location for Wattnet provider")
        location = location.upper()
        if location in WATTNET_ZONES:
            return location
        raise InvalidLocationError("Wattnet only supports zone names (e.g GB)")

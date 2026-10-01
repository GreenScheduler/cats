"""
Base API provider
-----------------

This module provides the base provider class from which all API providers for
CATS are derived from. To define a new provider, create a new class derived from
BaseProvider, overriding all the abstract methods and register it
using the ``@provider`` decorator to register the provider.
"""

# pyright: reportAny=none

from __future__ import annotations

import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, ClassVar
from zoneinfo import ZoneInfo

from ..cache import RETRY_STATUSES, Cache  # noqa: F401
from ..exceptions import InvalidMetricError, UnsupportedProviderError
from ..forecast import Timeseries
from ..version import user_agent

PROVIDERS: dict[str, type[BaseProvider]] = {}


@dataclass(frozen=True)
class LocationGroup:
    """A set of valid --location codes sharing one encoding

    :param heading: Short description of the encoding, e.g. "Bidding zones"
    :param locations: Code to human readable name (empty string if none)
    :param note: Optional extra line shown under the heading
    """

    heading: str
    locations: dict[str, str]
    note: str = ""


def fetch_url(url: str, headers: dict[str, str] | None = None) -> Any:
    """
    Fetch and decode json representation of a provider's forecast data

    The provider is responsible for formatting a `url` which typically includes
    location, time and format information for the desired forecast. This is
    either extracted from a cache (if the forecast has been requested before with
    the same URL) or requested from the provider. The provider can also add `headers`
    as needed. This function always includes the CATS user_agent in the headers
    used in the request. Successful responses are cached, decoded from json to
    python objects and returned to the provider (which is responsible for extracting
    the required information). Python objects may be returned as a dictionary or a list,
    depending on the structure of the json. Requests that fail with a transient
    error (see RETRY_STATUSES) or a connection error are retried up to 3 times
    with exponential backoff, honouring any Retry-After header. Failed requests may return empty
    dictionaries or lists, or may include debugging information. The provider is
    responsible for checking this.

    :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json.
    :raises requests.exceptions.HTTPError: If the HTTP request fails
    """
    # Use a global HTTP cache in the temp directory with the URL as the key.
    # Entries expire after a day. Failed attempts are not cached.
    cache = Cache(Path(tempfile.gettempdir()), expires_after=timedelta(days=1))
    headers = headers or {}
    headers.update(user_agent)
    response = cache.get(url, headers=headers)
    # Catch and raise any HTTP errors
    response.raise_for_status()
    return response.json()  # pyright: ignore[reportUnknownMemberType]


def align_to_resolution(timestamp: datetime, resolution_minutes: int) -> datetime:
    """
    Round a timestamp down to UTC and to the start of its resolution interval

    Providers use this to build cache-friendly request URLs: repeated calls
    within the same interval produce an identical URL and are served from
    the shared cache used by fetch_url(). Rounds *down* to the exact interval
    boundary, rather than a minute or two into it, since some upstream APIs
    filter on "interval start >= requested start" - requesting anything
    after the boundary can exclude the current in-progress interval and
    leave a gap between "now" and the first returned data point.

    :param timestamp: Timestamp to align; converted to UTC first if it isn't already
    :param resolution_minutes: Provider's temporal resolution, e.g. 15 or 30
    :return: timestamp rounded down to the start of its resolution interval, in UTC
    """
    timestamp = timestamp.astimezone(timezone.utc)
    patch_minute = (timestamp.minute // resolution_minutes) * resolution_minutes
    return timestamp.replace(minute=patch_minute, second=0, microsecond=0)


def minutes_to_end_of_day(
    timestamp: datetime, tz: ZoneInfo, days_ahead: int, resolution_minutes: int
) -> int:
    """
    Minutes from the aligned `timestamp` to the end of a local day, less one step

    For providers whose data runs up to the end of a calendar day in some
    market's timezone (e.g. "today and tomorrow") rather than for a fixed
    length of time from now, so the maximum duration depends on when it is asked.
    The last resolution step is dropped, matching the other providers.

    :param timestamp: The time of the request
    :param tz: Timezone whose calendar days define the data horizon
    :param days_ahead: 0 for the end of the local day of `timestamp`, 1 for
        the end of the following day, and so on
    :param resolution_minutes: Provider's temporal resolution
    :return: Maximum duration in minutes, never negative
    """
    start = align_to_resolution(timestamp, resolution_minutes)
    local_date = timestamp.astimezone(tz).date()
    end = datetime.combine(
        local_date + timedelta(days=days_ahead + 1), time.min, tzinfo=tz
    )
    minutes = (end - start).total_seconds() / 60  # aware: DST-correct
    return max(int(minutes) - resolution_minutes, 0)


def resolve_metric(
    requested: str | None, supported: frozenset[str], default: str
) -> str:
    """
    Validate and resolve which metric a provider call should use

    A provider that only ever serves one implicit metric (an empty
    `supported` set) doesn't need callers to pass --metric at all, and
    accepts anything callers pass through unchanged (there is nothing to
    validate against). A provider that declares SUPPORTED_METRICS falls back
    to `default` when `requested` is None, and rejects anything else not in
    `supported`.

    :raises InvalidMetricError: if `requested` is set but not in `supported`
    """
    if not supported:
        return requested or default
    if requested is None:
        return default
    if requested not in supported:
        raise InvalidMetricError(
            f"{requested!r} is not a supported metric for this provider. "
            f"Supported metrics: {sorted(supported)}"
        )
    return requested


class BaseProvider(ABC):
    "Base provider class from which API providers in CATS derive from"

    BASE_URL: ClassVar[str]
    # Metrics a provider can serve via --metric, e.g. {"carbon", "water"}.
    # Leave empty for a provider that only ever serves one implicit metric
    # (no --metric selection needed); DEFAULT_METRIC is then unused.
    SUPPORTED_METRICS: ClassVar[frozenset[str]] = frozenset()
    DEFAULT_METRIC: ClassVar[str | None] = None

    def __init__(
        self, api_data: dict[str, Any] | None = None, base_url: str | None = None
    ):
        self.api_data: dict[str, Any] | None = api_data
        self.base_url: str = base_url or self.BASE_URL

    @abstractmethod
    def validate_location(self, location: str | None) -> str:
        "Returns location if valid, otherwise raises InvalidLocationError"

    def list_locations(self, metric: str | None = None) -> list[LocationGroup]:
        """Returns the locations this provider accepts, for --list-locations

        Providers whose location scheme depends on the metric return one group
        per scheme when `metric` is None, or just the matching group otherwise.
        The default returns no groups, for providers that do not enumerate them.
        """
        return []

    @abstractmethod
    def get_max_duration_minutes(self, metric: str | None = None) -> int:
        "Returns maximum supported duration in minutes for a particular metric"

    @abstractmethod
    def get_temporal_resolution_minutes(self, metric: str | None = None) -> int:
        "Returns temporal resolution in minutes for a metric"

    @abstractmethod
    def get_data(
        self,
        timestamp: datetime,
        location: str | None = None,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """Retrieves data from provider API

        :param timestamp: Timestamp from which to start forecast data retrieval
        :param location: Location for which to start forecast data retrieval
        :param metric: Optional, if specified selects a specific metric from provider
        :param headers: Optional, if specified, passes additional headers, such as for authentication
        :return: Timeseries as a list of PointEstimate classes
        """


def provider(name: str) -> Callable[[type[BaseProvider]], type[BaseProvider]]:
    "Decorator to register a provider class with CATS"

    def decorator(cls: type[BaseProvider]):
        PROVIDERS[name] = cls
        return cls

    return decorator


def get_provider(name: str) -> type[BaseProvider]:
    if name in PROVIDERS:
        return PROVIDERS[name]
    raise UnsupportedProviderError(name)


def list_providers() -> dict[str, type[BaseProvider]]:
    "Return the registered providers, keyed by their --api name"
    return dict(PROVIDERS)

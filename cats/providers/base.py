"Base API provider"

# pyright: reportAny=none

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, ClassVar

import requests_cache

from ..exceptions import UnsupportedProviderError
from ..forecast import Timeseries
from ..version import user_agent

PROVIDERS: dict[str, type[BaseProvider]] = {}


def fetch_url(url: str, headers: dict[str, str] | None = None) -> Any:
    # Setup a session for the API call. This uses a global HTTP cache
    # with the URL as the key. Failed attempts are not cached.
    session = requests_cache.CachedSession("cats_cache", use_temp=True)
    headers = headers or {}
    headers.update(user_agent)
    return session.get(url, headers=headers).json()  # pyright: ignore[reportUnknownMemberType]


class BaseProvider(ABC):
    "Base provider class from which API providers in CATS derive from"

    MAX_DURATION_MINUTES: ClassVar[int]

    def __init__(self, location: str | None = None):
        self.location: str | None = self.validate_location(location)
        self.data: list[dict[str, Any]] | None = None

    @abstractmethod
    def validate_location(self, location: str | None) -> str:
        "Returns location if valid, otherwise raises InvalidLocationError"

    @abstractmethod
    def get_data(
        self,
        timestamp: datetime,
        metric: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Timeseries:
        """Retrieves data from provider API

        :param timestamp: Timestamp from which to start forecast data retrieval
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

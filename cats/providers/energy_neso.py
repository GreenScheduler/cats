from datetime import datetime, timezone
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import pandas as pd
from dateutil import relativedelta
from typing_extensions import override

from ..exceptions import ProviderResponseError
from ..forecast import PointEstimate, Timeseries
from .base import BaseProvider, fetch_url, provider


def utc_to_local(timestamp: datetime) -> datetime.date:
    """
    Corrects a known UTC datestamp into a local timezone. Currently unused.

    Was used to convert from UTC to BST

    :param timestamp: Timestamp to convert from UTC to local, should follow "%Y-%m-%dT%H:%M:%S" format
    """

    datefmt = "%Y-%m-%dT%H:%M:%S"

    try:
        utc_dt = datetime.strptime(timestamp, datefmt)
    except ValueError:  # check correct error type?
        print("The timestamp provided doesn't follow the %Y-%m-%dT%H:%M:%S format")

    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def futurehours(timestamp: datetime | str) -> int:
    """
    Determines number of hours in the future to the nearest 30 minutes for a given datetime object, or of a string that
    that are in format of %Y-%m-%dT%H%M

    We do currently update the dataframe with this info but the resulting values are not used

    :param timestamps: A Pandas Series of type `timestamp` to calculate futures from, should follow "%Y-%m-%dT%H:%M" format
    """

    now = datetime.now()

    if type(timestamp) is str:
        datefmt = "%Y-%m-%dT%H%M"
        timestamp = datetime.strptime(timestamp, datefmt)

    timestamp = timestamp.replace(tzinfo=None)
    rd = relativedelta.relativedelta(timestamp, now)

    # calculate the date difference from the relativedelta span
    then = now - rd
    # unlike normal timedelta 'then' is returned as a datetime
    # subtracting two dates will give you a timedelta
    # which contains the value you're looking for
    diff = now - then

    days, seconds = diff.days, diff.seconds
    hours = days * 24 + seconds / 3600

    return round(hours * 2) / 2


@provider("neso.energy")
class UKGenerationDemandProvider(BaseProvider):
    BASE_URL: ClassVar[str] = "https://api.neso.energy"
    ENDPOINT: ClassVar[str] = "7c0411cd-2714-4bb5-a408-adb065edf34d"

    @override
    def validate_location(self) -> None:
        """
        These endpoints are not geospatially aware, so can safely ignore this method
        """
        pass

    @override
    def get_max_duration_minutes(self) -> int:
        """
        Returns the maximum number of minutes of duration of the forecast.

        For the generation demand forecast, zero is the first forecasted data point which is 0030 for the day after tomorrow (i.e. *not* the current time).

        :return: integer of the number of minutes duration of the metric
        """

        # todo: should we _actually_ calculate this from the returned data, or is doing the theoretical max from what the API says ok?

        # 30 mins: 0030->0100 (day 1)
        # 23 hours: 0100->0000 (day 1)
        # 12 days of forecasting
        total_duration = 30 + 23 * 60 + 12 * 24 * 60
        return total_duration

    @override
    def get_temporal_resolution_minutes(self) -> int:
        """
        :return: integer of the number of minutes duration of the metric
        """

        return 30

    @override
    def get_data(self, metric: str) -> Timeseries:
        # do we need to specify the parameters and return type again because I've overridden the docstring from the ABC method?

        """
        Generates a `Timeseries` of `PointEstimate` scaled (0-1) generation demand forecast

         - first forecast is 0030 for the first day after tomorrow
         - last forecast is 0000 for 14 days from tomorrow (i.e. really the end of the day 2 weeks today)
         - this gives 13 * (2 * 24) data points = 624, and that's magically the number of rows in the returned data ✨
        """

        url = (
            f"{self.BASE_URL}/api/3/action/datastore_search?resource_id={self.ENDPOINT}"
        )
        response: dict[str, Any] | None = fetch_url(url)

        # todo: add logic for different neso.energy endpoints

        if response is None:
            raise ProviderResponseError

        data = response["result"]["records"]
        all_data = pd.DataFrame.from_dict(data)  # todo: limit fields

        all_data["localtime"] = all_data["GDATETIME"].apply(utc_to_local)
        all_data["futurehours"] = all_data["localtime"].apply(futurehours)
        future_demand = all_data["NATIONALDEMAND"]
        all_data["scaled"] = (future_demand - future_demand.min()) / (
            future_demand.max() - future_demand.min()
        )

        # Force TimeZone metadata into the datetime object
        datefmt = "%Y-%m-%dT%H:%M:%S"
        utc = ZoneInfo("UTC")
        values = [
            PointEstimate(
                datetime=datetime.strptime(d.GDATETIME, datefmt).replace(tzinfo=utc),
                value=round(d.scaled, 4),
            )
            for d in all_data.itertuples()  # iterating through a Pandas dataframe is considered pretty bad practice (even though this is small) - might be a way to vectorise this
        ]
        return Timeseries("Scaled generation demand forecast", values=values, unit=None)

from datetime import datetime, timezone
from typing import Any, ClassVar

from typing_extensions import override
from dateutil import relativedelta
from zoneinfo import ZoneInfo

import pandas as pd

from .base import BaseProvider, fetch_url, provider
from ..exceptions import ProviderResponseError
from ..forecast import Timeseries, PointEstimate

def utc_to_local(timestamp: datetime):

    """
        Corrects a known UTC datestamp into a local timezone. Currently unused. 
        
        Was used to convert from UTC to BST

        :param timestamp: Timestamp to convert from UTC to local, should follow "%Y-%m-%dT%H:%M:%S" format  
    """

    datefmt = "%Y-%m-%dT%H:%M:%S"

    try:
        utc_dt = datetime.strptime(timestamp, datefmt)
    except ValueError: # check correct error type?
        print("The timestamp provided doesn't follow the %Y-%m-%dT%H:%M:%S format")
    
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def futurehours(timestamps: pd.Series[datetime | str]) -> pd.Series:

    """
        Determines number of hours in the future in 30 minute increments for a given series of datetime objects, or strings that
        that are in format of %Y-%m-%dT%H%M, that are also at 30 minute intervals.

        Currently unused.

        :param timestamps: Series of timestamp to calculate futures from, should follow "%Y-%m-%dT%H:%M" format  
    """

    now = datetime.now()

    datefmt = "%Y-%m-%dT%H%M"

    if type(dto) == str:
        dto = datetime.strptime(dto, datefmt)

    dto = dto.replace(tzinfo=None)
    rd = relativedelta.relativedelta(dto,now)

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
    ENDPOINT = "7c0411cd-2714-4bb5-a408-adb065edf34d"

    @override
    def get_data(self) -> Timeseries:

        """
        Generates a `Timeseries` of `PointEstimate` scaled (0-1) generation demand forecast

         - first forecast is 0030 for the first day after tomorrow
         - last forecast is 0000 for 14 days from tomorrow (i.e. really the end of the day 2 weeks today)
         - this gives 13 * (2 * 24) data points = 624, and that's magically the number of rows in the returned data ✨

        """

        url = (
             f"{self.BASE_URL}"
             "/api/3/action/"
             "datastore_search?resource_id="
             f"{self.ENDPOINT}"
            )
        response: dict[str, Any] | None = fetch_url(url)

        if response is None:
            raise ProviderResponseError
        
        data = response.json()["result"]["records"]
        all_data = pd.DataFrame.from_dict(data) # todo: limit fields

        all_data["localtime"] = all_data["GDATETIME"].apply(utc_to_local)
        all_data["futurehours"] = all_data.iloc[:,7].apply(futurehours)
        future_demand = all_data["NATIONALDEMAND"]
        all_data["scaled"] = (future_demand - future_demand.min()) / (future_demand.max() - future_demand.min())


        # Force TimeZone metadata into the datetime object
        datefmt = "%Y-%m-%dT%H:%M:%S"
        utc = ZoneInfo("UTC")
        values = [
            PointEstimate(
                    datetime=datetime.strptime(d.GDATETIME, datefmt).replace(tzinfo=utc), 
                    value=round(d.scaled, 4) 
                )
            for d in all_data.itertuples()

        ]
        return Timeseries("Scaled generation demand forecast", values=values, unit=None)

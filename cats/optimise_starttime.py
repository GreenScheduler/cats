from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from .api_interface import CarbonIntensityEstimate

class starttime_optimiser():
    def __init__(self, CI_forecast):
        self.CI_forecast = CI_forecast

    def _calculate_averageCI_over_runtime(self, starttime, endtime):
        '''
        Calculate the total average CI between `starttime` and `endtime`
        by integrating over each time window (and taking into account the
        fact that first and last time windows are probably incomplete)
        :param starttime: [datetime]
        :param endtime: [datetime]
        :return: [float] average CI in CO2e
        '''
        # TODO deal with runtime running past end of forecast

        # Only keep the relevant windows in the total forecast
        filtered_forecast = [
            window for window in self.CI_forecast
            if starttime < window.end and window.start < endtime
        ]

        # Calculate average CI between starttime and endtime
        CIsec = 0 # in gCO2e x seconds
        totalsec = 0 # in seconds
        for window in filtered_forecast:
            # find the true duration of the window [timedelta]
            # (this is needed because first and last windows won't be a full 30min, or whatever the window size is)
            true_window = min(endtime, window.end) - max(starttime, window.start)
            CIsec += window.value * true_window.total_seconds()
            totalsec += true_window.total_seconds()

        return CIsec/totalsec

    def _get_all_averageCIs(self, duration):
        '''
        Calculate all the average CIs for all possible start times.
        The first possible time is now, the last possible time is "End of forecast - job duration".
        :param duration: [timedelta]
        :return: [list[CarbonIntensityEstimate]] All possible average CIs
        '''
        currenttime = datetime.now(timezone.utc)
        end_of_forecast = self.CI_forecast[-1].end

        all_averageCIs = []

        # What if we start the job now
        endtime = currenttime + duration
        assert endtime <= end_of_forecast, "Job is longer than total forecasted carbon intensities"

        all_averageCIs.append(CarbonIntensityEstimate(
            start=currenttime,
            end=endtime,
            value=self._calculate_averageCI_over_runtime(currenttime, endtime),
        ))

        # Go through all the possible starttimes and calculate average CIs
        for window in self.CI_forecast:
            starttime = window.start
            endtime = window.start + duration

            # It needs to be (1) a starttime in the future and (2) leave enough time to finish before the end of the forecast
            if starttime > currenttime and endtime <= end_of_forecast:
                all_averageCIs.append(CarbonIntensityEstimate(
                    start=starttime,
                    end=endtime,
                    value=self._calculate_averageCI_over_runtime(starttime, endtime),
                ))

        return all_averageCIs

    def get_starttime(self, duration):
        '''
        Find best possible starttime to minimise carbon intensities
        :param duration: [timedelta]
        :return: [tuple(CarbonIntensityEstimate, list[CarbonIntensityEstimate])]
        '''
        all_averageCIs = self._get_all_averageCIs(duration)
        # Find the minimum value
        all_averageCIs_sorted = sorted(all_averageCIs)

        return all_averageCIs_sorted[0], all_averageCIs_sorted
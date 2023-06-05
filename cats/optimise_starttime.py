from datetime import datetime, timezone, timedelta
import copy

from .CI_api_interface import CarbonIntensityEstimate

class windowed_forecast:
    def __init__(self, CI_forecast, method, override_currentime=None):
        self.CI_forecast = CI_forecast
        self.method=method
        self.override_currentime = override_currentime # For testing only

    def _calculate_averageCI_over_runtime(self, starttime, endtime, method):
        '''
        Calculate the total average CI between `starttime` and `endtime`
        by integrating over each time window (and taking into account the
        fact that first and last time windows are probably incomplete)
        :param starttime: [datetime]
        :param endtime: [datetime]
        :param method: [str] 'sum' assumes carbon intensity forecast is a staircase function.
        'trapezoidal' integrates between the starting points of each window.
        :return: [float] average CI in CO2e
        '''

        # Only keep the relevant windows in the total forecast
        # filtered_forecast = [
        #     window for window in self.CI_forecast
        #     if starttime < window.end and window.start < endtime
        # ]

        CIsec = 0  # in gCO2e x seconds
        totalsec = 0  # in seconds

        filtered_forecast_idx = [
            i for i in range(len(self.CI_forecast))
            if starttime < self.CI_forecast[i].end and self.CI_forecast[i].start < endtime
        ]

        for i in filtered_forecast_idx:
            window = self.CI_forecast[i]

            w_start_time = max(starttime, window.start)
            w_end_time = min(endtime, window.end)

            true_window_size = (w_end_time - w_start_time).total_seconds()
            totalsec += true_window_size

            if method == 'sum':
                # print("Window: ", window)
                # print(f"Values: ({w_start_time}, {window.value}), ({w_end_time})\n")

                ### Integrate using the window value
                CIsec += window.value * true_window_size

            elif method == 'trapezoidal':

                if i == len(self.CI_forecast)-1:
                    # this is the last window of the forecast, so we create a fake next window to be able to integrate
                    next_window = CarbonIntensityEstimate(
                        start = window.end,
                        end = window.end+timedelta(days=1),
                        value = window.value
                    )
                else:
                    next_window = self.CI_forecast[i+1]


                ### Find the start and end values for the integration window

                if starttime > window.start:
                    # this is the first window
                    w_value_start = self._infer_point_on_line(
                        time_a=window.start, value_a=window.value,
                        time_b=next_window.start, value_b=next_window.value,
                        point=starttime
                    )
                else:
                    w_value_start = window.value

                if endtime < window.end:
                    # this is the last window

                    w_value_end = self._infer_point_on_line(
                        time_a=window.start, value_a=window.value,
                        time_b=next_window.start, value_b=next_window.value,
                        point=endtime
                    )
                else:
                    w_value_end = next_window.value

                # print("Window: ", window)
                # print(f"Values: ({w_start_time}, {w_value_start}), ({w_end_time}, {w_value_end})\n")

                ### Integrate the window using trapezoidal rule
                CIsec += (w_value_start + w_value_end) / 2 * true_window_size

        return CIsec/totalsec

    def _infer_point_on_line(self, time_a, value_a, time_b, value_b, point):
        # For b between a and c, f(b) = f(a) + (f(c)-f(a))/(c-a) * (b-a)
        return value_a + (value_b - value_a)/(time_b - time_a).total_seconds() * (point - time_a).total_seconds()

    def _get_all_averageCIs(self, duration):
        '''
        Calculate all the average CIs for all possible start times.
        The first possible time is now, the last possible time is "End of forecast - job duration".
        :param duration: [timedelta]
        :return: [list[CarbonIntensityEstimate]] All possible average CIs
        '''
        if self.override_currentime is None:
            currenttime = datetime.now(timezone.utc)
        else:
            currenttime = self.override_currentime

        end_of_forecast = self.CI_forecast[-1].end

        # What if we start the job now
        endtime = currenttime + duration
        # TODO add the option to start jobs planned to run past end of forecast (i.e. with unknown CI for some of it)
        if endtime > end_of_forecast:
            raise ValueError(f"Job is longer than total forecasted carbon intensities (duration={duration.total_seconds()/3600:.1f} hours but only {(end_of_forecast - self.CI_forecast[0].start).total_seconds()/3600:.1f} hours available)")

        all_averageCIs = [CarbonIntensityEstimate(
            start=currenttime,
            end=endtime,
            value=self._calculate_averageCI_over_runtime(currenttime, endtime, method=self.method),
        )]

        # Go through all the possible starttimes and calculate average CIs
        for window in self.CI_forecast:
            starttime = window.start
            endtime = window.start + duration

            # It needs to be (1) a starttime in the future and (2) leave enough time to finish before the end of the forecast
            if starttime > currenttime and endtime <= end_of_forecast:
                all_averageCIs.append(CarbonIntensityEstimate(
                    start=starttime,
                    end=endtime,
                    value=self._calculate_averageCI_over_runtime(starttime, endtime, method=self.method),
                ))

        return all_averageCIs

    def get_starttime(self, duration):
        '''
        Find best possible starttime to minimise carbon intensities
        :param duration: [timedelta]
        :return: [tuple(CarbonIntensityEstimate, list[CarbonIntensityEstimate])]
        '''
        all_averageCIs = self._get_all_averageCIs(duration)

        return min(all_averageCIs), all_averageCIs
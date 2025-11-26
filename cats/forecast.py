from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta


@dataclass(order=True)
class CarbonIntensityPointEstimate:
    """Represents a single data point within an intensity
    timeseries. Use order=True in order to enable comparison of class
    instance based on the first attribute. See
    https://peps.python.org/pep-0557
    """

    value: float  # the first attribute is used automatically for sorting methods
    datetime: datetime

    def __repr__(self):
        return f"{self.datetime.isoformat()}\t{self.value}"


@dataclass(order=True)
class CarbonIntensityAverageEstimate:
    """Represents a single data point within an *integrated* carbon
    intensity timeseries. Use order=True in order to enable comparison
    of class instance based on the first attribute.  See
    https://peps.python.org/pep-0557
    """

    value: float
    start: datetime  # Start of the time-integration window
    end: datetime  # End of the time-integration window
    start_value: float  # CI point estimate at start time
    end_value: float  # CI point estimate at end time


class WindowedForecast:
    def __init__(
        self,
        data: list[CarbonIntensityPointEstimate],
        duration: int,  # in minutes
        start: datetime,
        max_window_minutes: Optional[int] = None,
        end_constraint: Optional[datetime] = None,
    ):
        self.duration = duration
        self.max_window_minutes = max_window_minutes
        self.end_constraint = end_constraint

        # Filter data based on constraints if any are specified
        if max_window_minutes is not None or end_constraint is not None:
            filtered_data = self._filter_data_by_constraints(
                data, start, duration, max_window_minutes or 2820, end_constraint
            )
        else:
            filtered_data = data

        self.data_stepsize = filtered_data[1].datetime - filtered_data[0].datetime
        self.start = start
        self.end = start + timedelta(minutes=duration)

        # Restrict data points so that start time falls within the
        # first data interval.  In other we don't need any data prior
        # the closest data preceding (on the left of) the job start
        # time.
        def bisect_right(data, t):
            for i, d in enumerate(data):
                if d.datetime > t:
                    return i - 1

        # bisect_right(data, start) returns the index of the first
        # data point with datetime value immediately preceding the job
        # start time
        self.data = filtered_data[bisect_right(filtered_data, start) :]

        # Find number of data points in a window, by finding the index
        # of the closest data point past the job end time. Could be
        # done with the bisect module in the stdlib for python 3.10+
        # ('key' parameter was introduced in 3.10).
        #
        # bisect_left(data, self.end, key=lambda x: x.datetime)
        #
        def bisect_left(data, t):
            for i, d in enumerate(data):
                if d.datetime + self.data_stepsize >= t:
                    return i + 1
            raise ValueError("No index found for closest data point past job end time")

        self.ndata = bisect_left(self.data, self.end)  # window size

    def _filter_data_by_constraints(
        self,
        data: list[CarbonIntensityPointEstimate],
        start: datetime,
        duration: int,
        max_window_minutes: int,
        end_constraint: Optional[datetime],
    ) -> list[CarbonIntensityPointEstimate]:
        """Filter forecast data based on time constraints."""

        # Calculate the maximum time we need data for
        search_window_end = start + timedelta(minutes=max_window_minutes)

        if end_constraint:
            # Ensure timezone compatibility
            if end_constraint.tzinfo != start.tzinfo:
                end_constraint = end_constraint.astimezone(start.tzinfo)
            # Jobs must start before end_constraint
            search_window_end = min(search_window_end, end_constraint)

        # We need data points to cover jobs starting up to search_window_end
        # plus the duration of those jobs
        max_data_time = search_window_end + timedelta(minutes=duration)

        # Filter data to respect the constraints
        filtered_data = []
        for d in data:
            if d.datetime <= max_data_time:
                filtered_data.append(d)
            else:
                break

        if len(filtered_data) < 2:
            raise ValueError(
                "Insufficient forecast data for the specified time window constraints. "
                "Try increasing --window or adjusting --end-window."
            )

        return filtered_data

    def __getitem__(self, index: int) -> CarbonIntensityAverageEstimate:
        """Return the average of timeseries data from index over the
        window size.  Data points are integrated using the trapeziodal
        rule, that is assuming that forecast data points are joined
        with a straight line.

        Integral value between two points is the intensity value at
        the midpoint times the duration between the two points.  This
        duration is assumed to be unity and the average is computed by
        dividing the total integral value by the number of intervals.
        """

        if index >= len(self):
            raise IndexError("Window index out of range")

        # Account for the fact that the start and end of each window
        # might not fall exactly on data points.  The starting
        # intensity is interpolated between the first (index) and
        # second data point (index + 1) in the window.  The ending
        # intensity value is interpolated between the last and
        # penultimate data points in the window.
        window_start = self.start + index * self.data_stepsize
        window_end = self.end + index * self.data_stepsize

        # lbound: carbon intensity point estimate at window start
        lbound = self.interp(
            self.data[index],
            self.data[index + 1],
            when=window_start,
        )
        # rbound: carbon intensity point estimate at window end
        # Handle case when last data point exactly matches last carbon intensity,
        # so there is no further data point to interpolate from.
        if index + self.ndata == len(self.data):
            rbound = self.data[-1]
        else:
            rbound = self.interp(
                self.data[index + self.ndata - 1],
                self.data[index + self.ndata],
                when=window_end,
            )
        # window_data <- [lbound] + [...bulk...] + [rbound] where
        # lbound and rbound are interpolated intensity values.
        window_data = [lbound] + self.data[index + 1 : index + self.ndata] + [rbound]
        acc = [
            0.5 * (a.value + b.value) * (b.datetime - a.datetime).total_seconds()
            for a, b in zip(window_data[:-1], window_data[1:])
        ]
        duration = window_data[-1].datetime - window_data[0].datetime
        return CarbonIntensityAverageEstimate(
            start=window_start,
            end=window_end,
            value=sum(acc) / duration.total_seconds(),
            start_value=lbound.value,
            end_value=rbound.value,
        )

    @staticmethod
    def interp(
        p1: CarbonIntensityPointEstimate,
        p2: CarbonIntensityPointEstimate,
        when: datetime,
    ) -> CarbonIntensityPointEstimate:
        """Return carbon intensity pt estimate at a time between data
        points, assuming points are joined by a straight line (linear
        interpolation).
        """
        timestep = (p2.datetime - p1.datetime).total_seconds()

        slope = (p2.value - p1.value) / timestep
        offset = (when - p1.datetime).total_seconds()

        return CarbonIntensityPointEstimate(
            value=p1.value + slope * offset,
            datetime=when,
        )

    def __iter__(self):
        for index in range(len(self)):
            yield self[index]

    def __len__(self):
        """Return number of valid forecast windows respecting all constraints."""
        base_length = len(self.data) - self.ndata

        if base_length <= 0:
            return 0

        max_valid_index = base_length - 1

        # Check max window constraint only if specified
        if self.max_window_minutes is not None:
            data_stepsize_minutes = self.data_stepsize.total_seconds() / 60
            max_index_by_window = int(self.max_window_minutes / data_stepsize_minutes)
            max_valid_index = min(max_valid_index, max_index_by_window)

        # Check end constraint
        if self.end_constraint:
            if self.end_constraint.tzinfo != self.start.tzinfo:
                end_constraint = self.end_constraint.astimezone(self.start.tzinfo)
            else:
                end_constraint = self.end_constraint

            # Find the maximum index where job start time is before end_constraint
            for i in range(min(base_length, max_valid_index + 1)):
                window_start = self.start + i * self.data_stepsize
                if window_start >= end_constraint:
                    max_valid_index = i - 1
                    break

        return max(0, max_valid_index + 1)

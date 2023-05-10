import bisect
from datetime import datetime, timedelta
from .timeseries_conversion import cat_converter, csv_loader

CACHE_PATH = "./timedata.csv"


def parsetime(datestr: str) -> datetime:
    """parse the date string
    param datestr: a date string from the api
    returns: a datetime value
    """
    return datetime.strptime(datestr, "%Y-%m-%dT%H:%MZ")


def timefromnow(time: datetime) -> tuple[int, float]:
    """calculate the time delta between now and a timestamp
    param time: a datetime timestamp
    returns: tuple containing time delta in seconds and a unix timestamp
    """
    currenttime = datetime.now()
    timediff = abs(currenttime - time)
    deltaseconds = timediff.seconds
    unixtime = time.timestamp()
    return (deltaseconds, unixtime)


def makedata(data: list[tuple[str, int]]) -> list[tuple[str, int, float, int]]:
    """create csv rows from api data
    param data: a set of tupics with start time and carbon intensity
    returns: a list of data table rows
    """
    output = []
    for d in data:
        timestr = d[0]
        time = parsetime(timestr)
        [deltaseconds, unixtime] = timefromnow(time)
        intensity = d[1]
        output.append((timestr, deltaseconds, unixtime, intensity))
    return output


def csvline(parseelement: tuple[str, int, float, int]) -> str:
    """write tuple of data row to string
    param parseelement: a parsed data row
    returns: a string of a data row
    """
    line = [str(x) for x in parseelement]
    return ",".join(line)


def writecsv(data: list[tuple[str, int]], duration=None) -> dict[str, int]:
    """write api data to csv
    param data: tuple of api output
    returns: None
    """
    parseddata = makedata(data)
    with open(CACHE_PATH, "w") as f:
        f.write("time,deltaseconds,unix,intensity\n")
        for d in parseddata:
            f.write(csvline(d))
            f.write("\n")
    # send data to timeseries processing code and print result
    return cat_converter(CACHE_PATH, "simple", duration)


def avg_carbon_intensity(start: datetime, runtime: timedelta):
    """Returns the averaged carbon intensity for a job given its start
    time and runtime.
    """
    data = csv_loader(CACHE_PATH)
    datetimes = [row[0] for row in data]
    intensities = [row[1] for row in data]

    # lo is the index of the data point coming just before (or equal
    # to) the start time
    lo = bisect.bisect(datetimes, start) - 1
    # hi is the index of the data point coming just after (or equal
    # to) the expected finish time
    hi = bisect.bisect(datetimes, start + runtime)

    return sum(intensities[lo : hi + 1]) / (hi - lo + 1)

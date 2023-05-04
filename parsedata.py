from datetime import datetime

outputfile = "./timedata.csv"


def parsetime(datestr: str) -> datetime:
    return datetime.strptime(datestr, "%Y-%m-%dT%H:%MZ")

def timefromnow(time: datetime) -> tuple[int, float]:
    currenttime = datetime.now()
    timediff = abs(currenttime - time)
    deltaseconds = timediff.seconds
    unixtime = time.timestamp()
    return (deltaseconds, unixtime)

def makedata(data: list) -> list[tuple[str, int, float, int]]:
    output = []
    for d in data:
        timestr = d[0]
        time = parsetime(timestr)
        [deltaseconds, unixtime] = timefromnow(time)
        intensity = d[1]
        output.append((timestr, deltaseconds, unixtime, intensity))
    return output
 
def csvline(parseelement: tuple[str, int, float, int]) -> str:
    line = [str(x) for x in parseelement]
    return ",".join(line)
    

def writecsv(data: list) -> None:
    parseddata = makedata(data)
    with open(outputfile, "w") as f:
        f.write("time,deltaseconds,unix,intensity\n")
        for d in parseddata:
            f.write(csvline(d))
            f.write("\n")


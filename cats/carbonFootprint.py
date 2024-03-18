import datetime
from collections import namedtuple

Estimates = namedtuple("Estimates", ["now", "best", "savings"])


def get_footprint_reduction_estimate(
    PUE: float,
    jobinfo: list[tuple[int, float]],
    runtime: datetime.timedelta,
    average_best_ci: float,  # in gCO2/kWh
    average_now_ci: float,
) -> Estimates:
    # energy in kWh
    energy = (
        PUE
        * (runtime.total_seconds() / 3600)
        * sum([(nunits * power) for nunits, power in jobinfo])
        / 1000
    )
    best = energy * average_best_ci
    now = energy * average_now_ci

    return Estimates(now, best, now - best)

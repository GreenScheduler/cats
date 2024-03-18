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

    return Estimates(*[format_footprint(e) for e in [now, best, now - best]])


def format_footprint(footprint_in_grams: float) -> str:
    """
    Format the text to display the carbon footprint
    :param footprint_g: [float] carbon footprint, in gCO2e
    :return: [str] the text to display
    """
    if footprint_in_grams < 1e3:
        return f"{footprint_in_grams:,.0f} gCO2e"
    if footprint_in_grams < 1e6:
        return f"{footprint_in_grams / 1e3:,.0f} kgCO2e"
    return f"{footprint_in_grams / 1e3:,.0f} TCO2e"

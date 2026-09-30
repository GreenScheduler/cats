import dataclasses
import json
import logging
from typing import Optional

from .carbonFootprint import Estimates
from .forecast import AverageEstimate


@dataclasses.dataclass
class CATSOutput:
    """
    Carbon Aware Task Scheduler output

    A dataclass to contain CATS output information for use
    with schedulers accompanied by methods to represent this
    information when reporting to users.
    """

    metric: str
    valueNow: AverageEstimate
    valueOptimal: AverageEstimate
    location: str
    countryISO3: str
    unit: str
    emmissionEstimate: Optional[Estimates] = None
    priceEstimate: Optional[Estimates] = None
    priceUnit: Optional[str] = None
    colour: bool = False

    def __str__(self) -> str:
        if self.colour:
            # Default colour
            col_normal = "\33[0m"  # reset any colour

            # Colours to indicate optimal/better results
            col_dt_opt = "\33[32m"  # green i.e. 'good' in traffic light rating
            col_ci_opt = "\33[32m"  # green
            col_ee_opt = "\33[32m"  # green

            # Colours to indicate original and non-optimal results
            col_ci_now = "\33[31m"  # red i.e. 'bad' in traffic light rating
            col_ee_now = "\33[31m"  # red
        else:
            col_normal = ""
            col_dt_opt = ""
            col_ci_opt = ""
            col_ci_now = ""
            col_ee_now = ""
            col_ee_opt = ""

        # Labels vary a lot in length depending on which metric/provider is in
        # use (e.g. "Carbon intensity" vs "Non-environmental score" vs a
        # composite's long "Composite score (...)" label), so the "=" column
        # is aligned dynamically rather than to hardcoded whitespace tuned
        # for one particular metric name. Capped so one pathologically long
        # label (e.g. composite's) doesn't drag every other line's padding
        # out with it; a label past the cap just gets a single space instead.
        lines: list[tuple[str, str]] = [
            (
                "Best job start time",
                f"{col_dt_opt}{self.valueOptimal.start:%Y-%m-%d %H:%M:%S}{col_normal}",
            ),
            (
                f"{self.metric} if job started now",
                f"{col_ci_now}{self.valueNow.value:.2f} {self.unit}{col_normal}",
            ),
            (
                f"{self.metric} at optimal time",
                f"{col_ci_opt}{self.valueOptimal.value:.2f} {self.unit}{col_normal}",
            ),
        ]

        if self.emmissionEstimate:
            lines.append(
                (
                    "Estimated emissions if job started now",
                    f"{col_ee_now}{self.emmissionEstimate.now}{col_normal}",
                )
            )
            lines.append(
                (
                    "Estimated emissions at optimal time",
                    f"{col_ee_opt}{self.emmissionEstimate.best} "
                    f"(- {self.emmissionEstimate.savings}){col_normal}",
                )
            )

        if self.priceEstimate:
            # Deliberately "at chosen start time", not "at optimal time": price is
            # reported here, not optimised for - the job start time above was chosen
            # for self.metric, not for lowest price. Unlike emmissionEstimate.savings
            # (always >= 0, since that metric is what's being optimised for),
            # priceEstimate.savings can be negative - the whole point of this report
            # is that optimising for another metric can make price *worse* - so show
            # an explicit sign instead of a literal "(- -71.24)".
            price_change = self.priceEstimate.savings
            sign = "-" if price_change >= 0 else "+"
            lines.append(
                (
                    "Price if job started now",
                    f"{col_ee_now}{self.priceEstimate.now:.2f} {self.priceUnit}{col_normal}",
                )
            )
            lines.append(
                (
                    "Price at chosen start time",
                    f"{col_ee_opt}{self.priceEstimate.best:.2f} {self.priceUnit} "
                    f"({sign} {abs(price_change):.2f}){col_normal}",
                )
            )

        max_label_width = 50
        label_width = min(max(len(label) for label, _ in lines), max_label_width)
        body = "\n".join(f"{label:<{label_width}} = {value}" for label, value in lines)
        out = f"\n{body}"

        logging.info("Use '--format=json' to get this in machine readable format")
        return out

    def to_json(self, dateformat: str = "", **kwargs) -> str:
        data = dataclasses.asdict(self)
        for val in ["valueNow", "valueOptimal"]:
            if dateformat == "":
                data[val]["start"] = data[val]["start"].isoformat()
                data[val]["end"] = data[val]["end"].isoformat()
            else:
                data[val]["start"] = data[val]["start"].strftime(dateformat)
                data[val]["end"] = data[val]["end"].strftime(dateformat)

        return json.dumps(data, **kwargs)

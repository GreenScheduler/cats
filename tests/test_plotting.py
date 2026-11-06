from datetime import datetime, timedelta, timezone

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from cats.forecast import AverageEstimate, PointEstimate, Timeseries
from cats.output import CATSOutput
from cats.plotting import _format_duration, plotplan


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (timedelta(minutes=30), "30m"),
        (timedelta(hours=2), "2h"),
        (timedelta(minutes=90), "1h 30m"),
    ],
)
def test_format_duration(duration: timedelta, expected: str) -> None:
    assert _format_duration(duration) == expected


def test_plotplan_labels_location_and_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    values = [PointEstimate(200 + i, start + timedelta(hours=i)) for i in range(24)]
    forecast = Timeseries("Carbon intensity", values, "gCO2eq/kWh")
    output = CATSOutput(
        "Carbon intensity",
        AverageEstimate(205, start, start + timedelta(hours=2), 205, 207),
        AverageEstimate(
            210,
            start + timedelta(hours=10),
            start + timedelta(hours=12),
            210,
            212,
        ),
        "London",
        "GBR",
        "gCO2eq/kWh",
    )

    monkeypatch.setattr(plt, "savefig", lambda *args, **kwargs: None)
    plotplan(forecast, output, "unused.png")

    fig = plt.gcf()
    try:
        ax = fig.axes[0]
        assert "Location: London" in [text.get_text() for text in ax.texts]
        labels = [text.get_text() for text in ax.get_legend().get_texts()]
        assert "If job started now (2h)" in labels
        assert "Optimal job window (2h)" in labels
    finally:
        plt.close(fig)

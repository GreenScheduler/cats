try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    have_matplotlib = True
except ImportError:
    have_matplotlib = False


def plotplan(CI_forecast, output):
    """
    Plot the carbon intensity forecast and optimised plan
    """
    if not have_matplotlib:
        print("To plot graphs you must import matplotlib")
        print("e.g. \"pip install 'climate-aware-task-scheduler[plots]'\"")
        return None

    # Just for now pull the CI forecast apart... probably belongs as method...
    values = []
    times = []
    now_values = []
    now_times = []
    opt_values = []
    opt_times = []
    # For our now and optimal series, start with the starting data (interpolated)
    opt_times.append(output.carbonIntensityOptimal.start)
    opt_values.append(output.carbonIntensityOptimal.start_value)
    now_times.append(output.carbonIntensityNow.start)
    now_values.append(output.carbonIntensityNow.start_value)
    # Build the three time series of point from the API
    for point in CI_forecast:
        values.append(point.value)
        times.append(point.datetime)
        if (
            point.datetime >= output.carbonIntensityOptimal.start
            and point.datetime <= output.carbonIntensityOptimal.end
        ):
            opt_values.append(point.value)
            opt_times.append(point.datetime)
        if (
            point.datetime >= output.carbonIntensityNow.start
            and point.datetime <= output.carbonIntensityNow.end
        ):
            now_values.append(point.value)
            now_times.append(point.datetime)
    # For our now and optimal series, end with the end data (interpolated)
    opt_times.append(output.carbonIntensityOptimal.end)
    opt_values.append(output.carbonIntensityOptimal.end_value)
    now_times.append(output.carbonIntensityNow.end)
    now_values.append(output.carbonIntensityNow.end_value)

    # Make the plot (should probably take fig and ax as opt args...)

    # Use an accessibility-approved colour scheme to ensure plot is
    # comprehendable for all (though also use hatching and clear text so
    # that no information is only encoded by colour choice/view)
    plt.style.use("tableau-colorblind10")
    forecast_colour = "tab:blue"
    now_colour = "tab:red"
    optimal_colour = "tab:green"

    fig, ax = plt.subplots()

    # Filling under curves for the forecast, run now time and optimal run time
    ax.fill_between(
        times,
        0.0,
        values,
        alpha=0.2,
        color=forecast_colour,
        edgecolor=forecast_colour,
        label="Forecast",
        linewidth=2.0,
    )
    # Show 'now' window in red with black hatch lines for contrast
    ax.fill_between(
        now_times,
        0.0,
        now_values,
        alpha=0.6,
        color=now_colour,
        label="If job started now",
        hatch="///",
        edgecolor="k",
        linewidth=1.0,
    )
    # Show 'optimal' window in green with hatch lines in opposite direction
    # but also in black: for any overlapping regions on the two windows, this
    # therefore results in a distinguishable cross-hatch pattern
    ax.fill_between(
        opt_times,
        0.0,
        opt_values,
        alpha=0.6,
        color=optimal_colour,
        label="Optimal job window",
        hatch="\\\\\\",
        edgecolor="k",
        linewidth=1.0,
    )

    # Add text to highlight values and for 'now' and 'optimal' job run times
    ax.text(
        0.125,
        1.075,
        f"Mean carbon intensity if job started now: {output.carbonIntensityNow.value:.2f} gCO2eq/kWh",
        transform=ax.transAxes,
        color=now_colour,
    )
    ax.text(
        0.125,
        1.025,
        f"Mean carbon intensity at optimal time: {output.carbonIntensityOptimal.value:.2f} gCO2eq/kWh",
        transform=ax.transAxes,
        color=optimal_colour,
    )

    ax.set_xlabel("Time (dd-mm-yy hh:mm)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%y %H:%M"))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%m-%y %H:%M"))
    ax.set_ylabel("Forecast carbon intensity (gCO2eq/kWh)")
    ax.label_outer()

    ax.grid(True)
    ax.legend()

    fig.autofmt_xdate()
    ax.set_ylim(bottom=0)  # start y-axis at 0, negative CI not possible!

    plt.show()

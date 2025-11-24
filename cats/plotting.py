try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter

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
        return

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

    # Determine if there is any window overlap, since then we add an extra
    # element to the legend to make clear how the overlap region looks but
    # otherwise we can leave it out. There will be an overlap if the end of
    # the 'now' time is more than the start of the optimal time since the
    # optimal is only ever time shifted forwards.
    windows_overlap = (
        output.carbonIntensityNow.end > output.carbonIntensityOptimal.start
    )

    # Make the plot (should probably take fig and ax as opt args...)

    # Use an accessibility-approved colour scheme to ensure plot is
    # comprehendable for all (though also use hatching and clear text so
    # that no information is only encoded by colour choice/view)
    plt.style.use("tableau-colorblind10")
    forecast_colour = "tab:blue"
    now_colour = "tab:red"
    optimal_colour = "tab:green"

    # Supply a figsize a bit different o the default (6.4, 4.8) to make the
    # plot a little bit more square else the x-axis label gets a bit cut off
    # due to long datetime labels
    fig, ax = plt.subplots(figsize=(7.0, 5.5))

    # Filling under curves for the forecast, run now time and optimal run time
    ax.fill_between(
        times,
        0.0,
        values,
        alpha=0.2,
        color=forecast_colour,
        edgecolor=forecast_colour,
        label="Forecast",
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
    )

    # In case the 'now' and 'optimal' windows overlap, is nice to show just
    # how that looks on legend, namely crosshatch in an (ugly) khaki colour
    # that represents the mixture of the transparent red and green. To do
    # this, use matplotlib's patches to create a proxy object i.e. patch.
    if windows_overlap:
        overlap_patch = Rectangle(
            # Arbitrary huge number to ensure dummy patch is outside plot area
            (1e10, 1e10),
            1,
            1,
            facecolor="#6f8d4a",  # mix colour from image colour picker tool
            edgecolor="k",
            hatch="////\\\\\\\\",
            label="Overlap area (now + optimal)",
            transform=ax.transAxes,  # << use axes coords instead of data coords
        )
        ax.add_patch(overlap_patch)
        handles, labels = ax.get_legend_handles_labels()
        handles.append(overlap_patch)
        labels.append(overlap_patch.get_label())
        ax.legend(handles=handles, labels=labels)

    now_value = output.carbonIntensityNow.value
    optimal_value = output.carbonIntensityOptimal.value
    # To avoid having to check if a user has (La)TeX available, to format the
    # units, use matploltib built-in lightweight TeX parser 'Mathtext' via
    # '$' symbols. Allows subscript on 2, etc. Needs a raw string to work.
    units = r"$\mathrm{g\,CO_{2}\,eq\;kWh^{-1}}$"

    ax.text(
        0.5,
        1.05,
        f"Projected carbon intensity ({units}) mean...",
        ha="center",
        va="bottom",
        fontsize=14,
        transform=ax.transAxes,
    )
    ax.text(
        0.45,
        1.0,
        f"...if job started now: {now_value:.2f}",
        ha="right",
        va="bottom",
        color=now_colour,
        fontsize=14,
        transform=ax.transAxes,
    )
    # Separator to divide the two described figures ('now' and 'optimal')
    ax.text(
        0.5,
        1.0,
        r"$\to$",
        ha="center",
        va="bottom",
        color="black",
        fontsize=14,
        transform=ax.transAxes,
    )
    ax.text(
        0.55,
        1.0,
        f"...at optimal time: {optimal_value:.2f}",
        ha="left",
        va="bottom",
        color=optimal_colour,
        fontsize=14,
        transform=ax.transAxes,
    )

    # For a nice illustration of CI saved, plot the lines corresponding to
    # the mean value for the 'now' and 'optimal' cases:
    plt.axhline(
        y=now_value,
        color=now_colour,
        linestyle="--",
        alpha=0.4,
        label="Mean if started now",
    )
    plt.axhline(
        y=optimal_value,
        color=optimal_colour,
        linestyle="--",
        alpha=0.4,
        label="Mean for optimal window",
    )

    # Include subtle markers at each data point, in case it helps to
    # distinguish forecast points from the trend (esp. useful if there)
    # is a similar trend across/for 1 hour or more i.e. 3+ data points
    ax.scatter(times, values, color=forecast_colour, s=8, alpha=0.3)
    ax.scatter(now_times, now_values, color=now_colour, s=8, alpha=0.3)
    ax.scatter(opt_times, opt_values, color=optimal_colour, s=8, alpha=0.3)

    def tick_formatting(x, pos):
        """Format datetimes so the x-axis labels become more readable.

        Namely, only show the full 'yy-mm-dd hh:mm' format date at the start
        of a day i.e. at hh:mm = 00:00, doing so in bold to provide emphasis.
        Otherwise show an ellipsis and then the hh:mm component only. This
        makes it much quicker for a reader to parse the date and time
        axis span and partitioning.
        """
        dt = mdates.num2date(x)

        # Would otherwise always full date at the first tick, as well as
        # at every point we get to a new day i.e. 00:00 (every four major
        # ticks), but then the date runs off the figure area to the left. So
        # it should be clear enough with two full dates plotted - which will
        # be the case always since we have a 48 hour window
        if dt.hour == 0 and dt.minute == 0:
            # Note \text{} required around '-' symbol else it is
            # interpreted as a minus sign and becomes so long with spacing
            # around that it pushes the x axis label off the figure below
            date_bold = dt.strftime(r"\mathbf{%y\text{-}%m\text{-}%d}")
            time_part = dt.strftime("%H:%M")
            return f"${date_bold}\ {time_part}$"

        # All other ticks → ellipsis + time
        time_part = dt.strftime("%H:%M")
        return f"$\ldots\ {time_part}$"

    # The x axis label needs some padding at the figure foot else it gets a
    # bit cut off due to the length of some datetime x labels
    ax.set_xlabel(r"Time ($\mathbf{yy\text{-}mm\text{-}dd}$ hh:mm)")
    ax.xaxis.set_major_formatter(FuncFormatter(tick_formatting))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%y-%m-%d %H:%M"))
    ax.set_ylabel(rf"Forecast carbon intensity ({units})")
    ax.label_outer()

    ax.grid(True)
    ax.legend()

    fig.autofmt_xdate()
    ax.set_ylim(bottom=0)  # start y-axis at 0, negative CI not possible!

    plt.subplots_adjust(bottom=0.20)
    plt.show()

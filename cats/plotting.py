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
        if (point.datetime >= output.carbonIntensityOptimal.start and
            point.datetime <= output.carbonIntensityOptimal.end):
            opt_values.append(point.value)
            opt_times.append(point.datetime)
        if (point.datetime >= output.carbonIntensityNow.start and
            point.datetime <= output.carbonIntensityNow.end):
            now_values.append(point.value)
            now_times.append(point.datetime)
    # For our now and optimal series, end with the end data (interpolated)
    opt_times.append(output.carbonIntensityOptimal.end)
    opt_values.append(output.carbonIntensityOptimal.end_value)
    now_times.append(output.carbonIntensityNow.end)
    now_values.append(output.carbonIntensityNow.end_value)

    # Make the plot (should probably take fig and ax as opt args...)
    fig, ax = plt.subplots()
    ax.fill_between(times, 0.0, values, alpha=0.2, color='b')
    ax.fill_between(now_times, 0.0, now_values, alpha=0.6,  color='r')
    ax.fill_between(opt_times, 0.0, opt_values, alpha=0.6, color='g')

    ax.text(0.125, 1.075, f"Mean carbon intensity if job started now: {output.carbonIntensityNow.value:.2f} gCO2eq/kWh",
             transform=ax.transAxes, color='red')
    ax.text(0.125, 1.025, f"Mean carbon intensity at optimal time: {output.carbonIntensityOptimal.value:.2f} gCO2eq/kWh",
             transform=ax.transAxes, color='green')

    ax.set_xlabel("Time (dd-mm-yy hh)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%y %H:%M"))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%d-%m-%y %H:%M"))
    ax.set_ylabel("Forecast carbon intensity (gCO2eq/kWh)")
    ax.grid(True)
    ax.label_outer()
    fig.autofmt_xdate()
    plt.show()
    return None
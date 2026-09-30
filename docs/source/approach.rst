.. _approach:

Approach and Implementation
===========================

The approach and implementation of CATS is described in a short paper published in the Journal
of Open Source Software (`doi:10.21105/joss.08251 <https://doi.org/10.21105/joss.08251>`_). Here
we describe how CATS works and fits alongside other approaches to green scheduling in more detail.

Background
----------

There are several approaches that have been proposed and/or implemented to reduce the carbon footprint
of computing. These include:

* interventions in procurement to maximize the useful life of computer hardware and thus reduce the embodied carbon cost;
* exercises in code modification to reduce the carbon cost of a particular calculation, mostly by shortening the runtime or reducing resource needs;
* modifying default settings to reduce carbon use; and
* attempts to improve data centre efficiency - for example, the clock frequency on ARCHER2, the UK national supercomputer, is now lower by default :cite:p:`Jackson23`.

However, many of these can be difficult for individual researchers to implement. One
more direct approach is to make use of lower carbon intensive electricity to power the
computation. One way this can be achieved is by relocating the computer to a part of the world where
electricity is generated using renewable means. For example, the University of York in the UK have located
the latest institutional computing resource in Sweden :cite:p:`Norsecode`.

Another approach is time shifting the computation such that it runs when the power
supplied by the local electricity grid is dominated by renewable generation such as
on windy or sunny days rather than periods where legacy fossil fuel generation
dominates. Minimally-invasive time-shifting approaches have been shown to
result in significantly reduced carbon footprints, by up to 27% in one AI benchmark :cite:p:`Dodge2022`. In a country
like the UK, these reductions can reach over 60% by shifting workload by a day or two :cite:p:`ElectricityMaps`.
CATS helps researchers timeshift their own computation such that it is scheduled when the forecast
carbon intensity of the power grid is minimised.

The CATS software
-----------------

At its core CATS is an open-source (MIT licence) Python package that
combines data on the forecast carbon intensity of the local electricity supply with information about
a proposed job's duration to assess the best start time of the computation within the validity interval
of the forecast. Users typically interact with CATS via a command-line interface targeting the UNIX
Shell (CATS is tested on Linux and MacOS) and the best start time can be provided in an informative
format (that the user can then use with their infrastructure) or in a way that can be passed on to job
schedulers to set the calculation start time. CATS is available via the Python Package Index (PyPI)
and can be installed along with its handful of dependencies into a Python environment with `pip`.

At a minimum, the user must provide CATS with the duration of the proposed computation and information about the location where the computation is to happen. This
can be provided on the command line, via a configuration file, or from geolocation of the IP address
and is sufficient information for CATS to access a prediction of the carbon intensity of the relevant
power distribution network which is used to compute the start time that minimises the carbon intensity
over the duration of the computation.

.. code-block:: console
   :caption: *Minimal example of the use of CATS on the command line with a postcode and duration provided.*

   $ cats --duration 480 --location "EH8"
   ...

   The.____ ..... __ .... ________ . ______...
   .. /  __)...../  \....(__    __).)  ____)....
   ..|  /......./    \......|  |...(  (___........
   ..| |limate./  ()  \ware.|  |ask.\___  \cheduler
   ..|  \__...|   __   |....|  |....____)  )....
   ...\    )..|  (..)  |....|  |...(      (..


   Best job start time                       = 2026-01-22 01:43:27
   Carbon intensity if job started now       = 43.23 gCO2eq/kWh
   Carbon intensity at optimal time          = 1.66 gCO2eq/kWh


At the moment, CATS is available for the UK through the National Grid's API which provides
postcode-specific 48 hour forecasts broken down into 30 minute periods. This granular data contains
regional distribution networks making use of a parameterised model of the power distribution system
in Great Britain, weather forecasts and historical generation data. A brief overview of the forecast
methodology can be found in :cite:t:`Bruce21a` and :cite:t:`Bruce21b` and the forecast, in the form of estimated carbon
intensity at the end of each half hour period, is available via a web API
(https://carbonintensity.org.uk/). CATS caches requests for this data to avoid repeated requests
within the thirty-minute time frame of a single forecast.

We have designed CATS in a modular way to enable future integration of other APIs in a
straightforward manner and also currently support the experimental API provided by the
https://wattnet.eu/ project for locations across Europe. We note that this API requires
authentication and for users to register an email address and obtain a password. The wattnet.eu
API provides data for about 60 zones across Europe (inside and outside the EU) with 72 hour
forecasts broken down into 15 minute periods. New APIs can be added by creating new implementations
of the `cats.providers.BaseProvider` abstract base class and registering these as documented elsewhere.

A single provider represents one API portal, which can serve more than one metric: which metric to
request is chosen with ``--metric`` (each provider declares a default, so a command that never
passes ``--metric`` is unaffected). ``wattnet.eu`` serves four metrics from three separate endpoints
of its own API: ``carbon`` (the default carbon intensity metric described above),
``water`` (life-cycle water footprint, l/kWh), ``water_stress`` (water-stress-weighted
footprint, stress-l/kWh, accounting for local water scarcity rather than plain volume), and
``environmental_score`` (wattnet's own composite score, where higher is better; CATS inverts it,
consistent with every other metric CATS reports).

Beyond carbon intensity, CATS also supports scheduling to minimise electricity *cost* rather than
carbon, via a ``price`` metric on two further providers returning day-ahead electricity price
forecasts: the ``energy-charts.info`` provider (Fraunhofer ISE, 54 European bidding zones, excluding
Great Britain, which is outside the EU single day-ahead market coupling this data is sourced from)
and the ``octopus.energy`` provider (the Agile Octopus tariff, tracking the GB wholesale day-ahead
price, covering the same 14 GB distribution regions as the NESO carbon intensity provider). Both
require no authentication. Since lower price is "better" in the same way lower carbon intensity is,
this metric reuses the same minimisation logic described above unmodified; only the metric name and
unit returned differ.

A further metric is renewable generation share, served as ``renewables`` on ``energy-charts.info``
(continental Europe) and on ``carbonintensity.org.uk`` (Great Britain, derived from the same
regional API response that provider already fetches for ``carbon``, requiring no extra external
API). Maximising renewable share does not always coincide with minimising carbon intensity (nuclear
generation is low-carbon but not renewable) or price, making it a genuinely different scheduling
signal. Since "higher renewable share is better" is the opposite polarity to the "lower is better"
assumption built into the scheduler, this metric instead reports *non-renewable* share (100 minus
the renewable percentage), so the same minimisation logic applies unmodified here too.

CATS also has a single ``composite`` provider that trades off any combination of the signals above
rather than optimising for a single one, across both Great Britain and continental Europe. It
auto-detects whether the location it is given is a UK postcode outward code or a wattnet.eu zone
code, and for each requested signal picks whichever portal natively serves it for that kind of
location (e.g. for a UK postcode, ``carbon`` and ``renewables`` come from ``carbonintensity.org.uk``
and ``price`` from ``octopus.energy``; for a wattnet.eu zone, ``carbon`` comes from ``wattnet.eu``
and ``price``/``renewables`` from ``energy-charts.info``), falling back to wattnet.eu's ``GB`` zone,
with a logged warning, only for the three wattnet-only signals (``water``,
``water_stress``, ``environmental_score``) when given a UK postcode. It independently min-max
normalises each selected series over the fetched forecast window, and combines them into a single
score with configurable weights, set via the repeatable ``--signal NAME=WEIGHT`` option (e.g.
``--signal carbon=0.4 --signal price=0.3 --signal renewables=0.3``; weights are normalised
automatically and don't need to sum to 1). With no ``--signal`` given, every signal available for
that location that needs no extra authentication is combined with equal weight. Because the result
is still an ordinary ``Timeseries`` of normalised scores where lower is better, the same
minimisation logic applies unmodified; no changes were needed to the scheduling algorithm itself to
support this trade-off, only to the composite provider combining the signals that feed into it.

Blending ``price`` into that weighted score, however, still lets price dominate the outcome if given
enough weight, which risks drifting away from CATS' climate-aware purpose entirely (e.g. a
``carbon=0.05``/``price=0.95`` blend would be a cost optimiser wearing a climate-aware label). As a
safer default, ``cats/pricing.py`` lets price act as a **constraint** instead of a blended weight:
whichever metric is actually being optimised (single-provider or composite) keeps being optimised for,
but candidate start times are restricted to those whose price does not exceed a cap, set via
``--max-price`` (an absolute cap) or ``--max-price-increase-pct`` (a cap relative to the price of
running the job right now). This works for any provider or metric, not just ``composite``, by
resolving a price series for the location independently of what is actually being optimised, reusing
``CompositeProvider``'s existing location-aware price routing rather than duplicating it. If no
candidate window both satisfies the cap and falls within whatever forecast horizon price data
currently covers - which is often considerably shorter than the metric being optimised, since
day-ahead prices are typically only published a matter of hours to a couple of days ahead - CATS
raises a clear error rather than silently falling back to the unconstrained optimum or picking an
unverified window. Independently of whether either flag is given, CATS also reports the price impact
of the chosen schedule whenever price data covers both the "now" and the chosen start time, so the
cost consequence of an environmental-metric-only optimisation is always visible without price ever
silently influencing that optimisation itself.

With the carbon intensity forecast and duration of the proposed computation in hand, the next task
is to locate the start time (within the valid forecast period) that minimises the integrated carbon
intensity over a sliding window equal to the duration. All else being equal, this minimising start
time is the time when the carbon cost of the proposed computation will be least. The difference in
the integrated carbon footprint between an optimal start time and starting the calculation immediately
is a measure of the potential benefits of timeshifting the computation. An illustration of this
calculation is provided in Figure 1. Once the carbon intensity minimisation has been completed,
CATS can optionally submit the computation to a queueing system or make a more detailed report on the
climate impact of the proposed computation.

.. figure:: _static/example_plot_output_rg1_180mins.png
  :width: 400
  :alt: CATS command run plot example output for RG1 and 3 hour job.
     The graph shows the forecast carbon intensity, a red region representing running the job now and
     a green region of lower intensity representing running the job in the future.
  :align: center

  Figure 1. Illustration of the carbon intensity time series (blue) with the predicted carbon use for
  running a three hour calculation now (red) or at a time that minimizes the integrated carbon
  intensity (green). Such a plot can be generated with CATS using the ``--plot`` option.

Submitting the computation to a queueing system can take just one more step, most clearly illustrated
by using the veritable `at` program available on most Linux and MacOS systems. The `at` program
“queues jobs for later execution” and, assuming the user provides the command to run their computation
and any necessary arguments using the CATS `--command` option, the computation can be scheduled to run
at the optimal time through delayed start activated with the `at` CLI. The options for the time syntax
for `at` on different systems are mutually incompatible, so CATS restricts itself to the POSIX
compatible time format. CATS also supports job submission to other queueing systems such as SLURM.

Providing further information about the carbon cost of the proposed computation improves the
educational impact of CATS. This can be enabled with the `--footprint` command-line option.
This calculation follows that used by the Green Algorithms project :cite:p:`Lannelongue21`, which also
provides some easy to understand "equivalent" statements to put these numbers in context. To
provide this footprint information CATS must be configured with information about the hardware
(principally the per-core power consumption of the processors) via "profiles" in the configuration
file. Different profiles can allow for different classes of computation (for example, one that
only uses the CPU, or one that uses the CPU and an attached GPU). This information, together with
the grid carbon intensity and job duration, allows the total power consumption of the computation
to be estimated along with the implied CO\ :sub:`2` cost if it were to be run now, or if the start time
were to be delayed to minimise the carbon intensity. In addition, this information can be included
in graphical output.

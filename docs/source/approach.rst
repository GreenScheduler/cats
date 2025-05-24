.. _approach:

Approach and Implementation
===========================

There are several approaches that have been proposed and/or implemented to reduce the carbon footprint 
of computing. These include interventions in procurement to maximise the useful life of computer 
hardware and thus reduce the embodied carbon cost; exercises in code modification to reduce the 
carbon cost of a particular calculation, mostly by shortening the runtime or reducing resource needs; 
modifying default settings to reduce carbon use [e.g. the clock frequency on ARCHER2, the UK national 
supercomputer, is now lower by default, @Jackson23]; and attempts to improve data centre efficiency. 
However, many of these can be difficult for individual researchers to implement. One 
easier-to-implement approach is to make use of lower carbon intensive electricity to power the 
computation. This can be achieved either by relocating the computer to a part of the world where 
electricity is generated using renewable means [e.g. the University of York in the UK have located 
the latest institutional computing resource in Sweden @Norsecode], or by time shifting the computation 
such that it runs when the power supplied by the local electricity grid is dominated by renewable 
generation such as on windy or sunny days rather than periods where legacy fossil fuel generation 
dominates. The potential impact of minimally-invasive time-shifting approaches has been shown to 
result in significantly reduced carbon footprints [27% in one AI benchmark @Dodge2022]. In a country 
like the UK, these reductions can reach over 60% by shifting workload by a day or two [@ElectricityMaps]. 
CATS helps researchers timeshift their own computation such that it is scheduled when the forecast 
carbon intensity of the power grid is minimised.

At its core CATS is an open-source (MIT licence) Python package (tested with Python 3.9-3.12) that 
combines data on the forecast carbon intensity of the local electricity supply with information about 
a proposed job's duration to assess the best start time of the computation within the validity interval 
of the forecast. Users typically interact with CATS via a command-line interface targeting the UNIX 
Shell (CATS is tested on Linux and MacOS) and the best start time can be provided in an informative 
format (that the user can then use with their infrastructure) or in a way that can be passed on to job 
schedulers to set the calculation start time. CATS is available via the Python Package Index (PyPI) 
and can be installed along with its handful of dependencies into a Python environment with pip. 
Development takes place on GitHub (https://github.com/GreenScheduler/cats) and documentation is
 available (https://greenscheduler.github.io/cats/).

At a minimum, the user must provide CATS with the duration of the proposed computation on the command 
line and CATS also requires information about the location where the computation is to happen. This 
can be provided on the command line, via a configuration file, or from geolocation of the IP address 
and is sufficient information for CATS to access a prediction of the carbon intensity of the relevant 
power distribution network which is used to compute the start time that minimises the carbon intensity 
over the duration of the computation.

At the moment, CATS is available for the UK through the National Grid's API which provides 
postcode-specific 48 hour forecasts broken down into 30 minute periods. This granular data contains 
regional distribution networks making use of a parameterised model of the power distribution system 
in Great Britain, weather forecasts and historical generation data. A brief overview of the forecast 
methodology can be found in [@Bruce21a; @Bruce21b] and the forecast, in the form of estimated carbon 
intensity at the end of each half hour period, is available via a web API 
(https://carbonintensity.org.uk/). CATS caches requests for this data to avoid repeated requests 
within the thirty minute time frame of a single forecast. We have designed CATS in a modular way to 
enable future integration of other countries' APIs in a straightforward manner. However, to date, we 
are unaware of any publicly accessible forecasts of carbon intensity for other regional, national or 
transnational electricity distribution networks.

With the carbon intensity forecast and duration of the proposed computation in hand, the next task 
is to locate the start time (within the valid forecast period) that minimises the integrated carbon 
intensity over a sliding window equal to the duration. All else being equal, this minimising start 
time is the time when the carbon cost of the proposed computation will be least. The difference in 
the integrated carbon footprint between an optimal start time and starting the calculation immediately 
is a measure of the potential benefits of timeshifting the computation. An illustration of this 
calculation is provided in Figure 1. Once the carbon intensity minimisation has been completed, 
CATS can optionally submit the computation to a queueing system or make a more detailed report on the 
climate impact of the proposed computation.

Submitting the computation to a queueing system can take just one more step, most clearly illustrated 
by using the veritable `at` program available on most Linux and MacOS systems. The `at` program 
“queues jobs for later execution” and, assuming the user provides the command to run their computation 
and any necessary arguments using the CATS `--command` option, the computation can be scheduled to run 
at the optimal time through delayed start activated with the `at` CLI. The options for the time syntax 
for `at` on different systems are mutually incompatible, so CATS restricts itself to the POSIX 
compatible time format. CATS also supports job submission to other queuing systems such as slurm.

![illustration of the carbon intensity time series for (blue) with the predicted energy use for 
running a twelve hour calculation now (red) or at a time that minimises the integrated carbon 
intensity (green).\label{fig:schedule}](fig1.png)

Providing further information about the carbon cost of the proposed computation improves the 
educational impact of CATS. This can be enabled with the `--footprint` command-line option. 
This calculation follows that used by the Green Algorithms project [@Lannelongue21], which also 
provides some easy to understand “equivalent” statements to put these numbers in context. To 
provide this footprint information CATS must be configured with information about the hardware 
(principally the per-core power consumption of the processors) via “profiles” in the configuration 
file. Different profiles can allow for different classes of computation (for example, one that 
only uses the CPU, or one that uses the CPU and an attached GPU). This information, together with 
the grid carbon intensity and job duration, allows the total power consumption of the computation 
to be estimated along with the implied CO$_2$ cost if it were to be run now, or if the start time 
were to be delayed to minimise the carbon intensity. In addition, this information can be included 
in graphical output.
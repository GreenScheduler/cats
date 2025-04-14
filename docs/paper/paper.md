---
title: 'CATS: The Climate Aware Task Scheduler'
tags:
  - Python
authors:
  - name: Sadie L. Bartholomew
    orcid: 0000-0002-6180-3603
    affiliation: "1, 2"
  - name: Lincoln Colling
    orcid: 0000-0002-3572-7758
    affiliation: 3
  - name: Abhishek Dasgupta
    orcid: 0000-0003-4420-0656
    affiliation: 4
  - name: Anthony J. Greenberg
    orcid: 0000-0003-3296-5811
    affiliation: 5
  - name: Loïc Lannelongue
    orcid: 0000-0002-9135-1345
    affiliation: "6,7,8"
  - name: Thibault Lestang
    orcid: 0000-0001-6770-2638
    affiliation: 9
  - name: Carlos Martinez-Ortiz
    orcid: 0000-0001-5565-7577
    affiliation: 10
  - name: Colin Sauzé
    orcid: 0000-0001-5368-9217
    affiliation: 11
  - name: Andrew M. Walker
    orcid: 0000-0003-3121-3255
    corresponding: true
    affiliation: 12
  - name: Adam Stuart Ward
    orcid: 0009-0008-3463-2694
    affiliation: 13
affiliations:
 - name: National Centre for Atmospheric Science, Fairbairn House, 71-75 Clarendon Road, Leeds, LS2 9PH, United Kingdom
   index: 1
 - name: Department of Meteorology, Brian Hoskins Building, University of Reading, Whiteknights campus, RG6 6ET, United Kingdom
   index: 2
 - name: School of Psychology, University of Sussex, Brighton, United Kingdom
   index: 3
 - name: Oxford Research Software Engineering Group, Doctoral Training Centre, University of Oxford, 1-4 Keble Road, Oxford, OX1 3NP, United Kingdom
   index: 4
 - name: Bayesic Research, Ithaca, NY, USA
   index: 5
 - name: British Heart Foundation Cardiovascular Epidemiology Unit, Department of Public Health and Primary Care, University of Cambridge, Cambridge, United Kingdom
   index: 6
 - name: Victor Phillip Dahdaleh Heart and Lung Research Institute, University of Cambridge, Cambridge, United Kingdom
   index: 7
 - name: Health Data Research UK Cambridge, Wellcome Genome Campus and University of Cambridge, Cambridge, United Kingdom
   index: 8
 - name: CNRM, Université de Toulouse, Météo-France, CNRS, Toulouse, France
   index: 9
 - name: Netherlands eScience Center, Science Park 402 (Matrix THREE), 1098 XH Amsterdam, Netherlands
   index: 10
 - name: National Oceanography Centre, Joseph Proudman Building, 6 Brownlow Street, Liverpool, L3 5DA, United Kingdom
   index: 11
 - name: Department of Earth Sciences, University of Oxford, South Parks Road, Oxford, OX1 3AN, United Kingdom
   index: 12
 - name: National Oceanography Centre, European Way, Southampton, SO14 3ZH, United Kingdom
   index: 13
date: 14 April 2025
bibliography: paper.bib

---

# Summary
The environmental impact of research computing is increasingly a topic of concern for researchers. One of the main contributors of compute-related greenhouse gas (GHG) emissions is the production of electricity to power digital research infrastructures (DRIs). The carbon footprint of electricity consumption (called carbon intensity) depends mostly on the energy mix of the grid (i.e. the share of renewable vs high-carbon production methods) which varies greatly with time and location. Here, we describe the Climate Aware Task Scheduler (CATS) which lets researchers schedule computing when low-carbon electricity is available. CATS leverages carbon intensity forecasts, e.g. from the power grid operators, to find the best window of time to run a particular job with minimal climate cost. CATS also provides an assessment of the carbon savings due to delaying compute (vs compute happening now). We also demonstrate how the tool benefits researchers in the UK using the country's national grid's forecasts.

# Statement of need

The climate impact of research computing, computer science, and computational science is hard to understate. Computing impacts the environment in many ways, from water and abiotic resource usage to GHG emissions from energy consumption and electronic waste. For many researchers, the CO$_2$e (CO$_2$-equivalent, the usual metric of carbon footprint aggregating the main GHGs) cost associated with running their models is larger than that of any other aspects of their life [@PortegiesZwart_2020]. For example, the global carbon footprint of data centres is estimated at 126 Mt CO$_2$e [@Malmodin2024], equivalent to the entire American commercial aviation sector, and individual computing projects can reach dozens, if not hundreds, of tonnes of CO$_2$e [@PortegiesZwart_2020; @GrealeyLannelongue2022; @Luccioni_Viguier_Ligozat_2022]. This is becoming clear to researchers and funders, who are exploring different approaches to reducing and accounting for the climate impact of the research they commission [@Weber_2024; @Juckes23; @Lannelongue_Fropier_Matencio_2025]. There is a clear need to provide tools for motivated researchers to minimise the detrimental contribution of their research on the climate emergency, and to educate researchers around this impact.

There are several approaches that have been proposed and/or implemented to reduce the carbon footprint of computing. These include interventions in procurement to maximise the useful life of computer hardware and thus reduce the embodied carbon cost, exercises in code modification to reduce the carbon cost of a particular calculation (mostly by shortening the runtime or reducing resource needs), modifying default settings to reduce carbon use [e.g. the clock frequency on ARCHER2, the UK national supercomputer, is now lower by default, @Jackson23] and attempts to improve data centre efficiency. However, many of these can be difficult for individual researchers to implement. One easier-to-implement approach is to make use of lower carbon intensive electricity to power the computation. This can be achieved either by shifting the computer to a part of the world where electricity is generated using renewable means [e.g. the University of York in the UK have located the latest institutional computing resource in Sweden @Norsecode], or by time shifting the computation such that it runs when the power supplied by the local electricity grid is dominated by renewable generation (e.g. on windy or sunny days) rather than periods where legacy fossil fuel generation dominates. The potential impact of minimally-invasive time-shifting approaches has been shawn to result in significantly reduced carbon footprints [27% in one AI benchmark @Dodge2022]. In a country like the UK, these reductions can reach over 60% by shifting workload by a day or two [@ElectricityMaps]. CATS helps researchers timeshift their own computation such that it is scheduled when the forecast carbon intensity of the power grid is minimised. 

# Approach and functionality

At its core CATS is an open source (MIT licence) python package (tested with python 3.9-3.12) that combines data on the forecast carbon intensity of the local electricity supply with information about a proposed job's duration to assess the best start time of the computation within the validity interval of the forecast. Users typically interact with CATS via a command line interface targeting the UNIX Shell (CATS is tested on Linux and MacOS) and the best start time can be provided in an informative format (that the user can then use with their infrastructure) or in a way that can be passed on to job schedulers to set the calculation start time. CATS is available via the python package index (pypi) and can be installed along with its handful of dependencies into a python environment with pip. Development takes place on github (https://github.com/GreenScheduler/cats) and documentation is available at (https://greenscheduler.github.io/cats/).

At a minimum, the user must provide CATS with the duration of the proposed computation on the command line and CATS also requires information about the location where the computation is to happen (this can be provided on the command line, via a configuration file, or from geolocation of the IP address). This is sufficient information for CATS to access a prediction of the carbon intensity of the relevant power distribution network which is used to compute the start time that minimises the carbon intensity over the duration of the computation.

At the moment, CATS is available for the UK through the National Grid's API which provides postcode-specific 48 hour forecasts broken down in 30 minute periods. This granular data contains regional distribution networks making use of a parameterised model of the power distribution system in Great Britain, weather forecasts and historical generation data. A brief overview of the forecast methodology can be found in [@Bruce21a; @Bruce21b] and the forecast, in the form of estimated carbon intensity at the end of each half hour period, is available via a web API (https://carbonintensity.org.uk/). CATS caches requests for this data to avoid repeated requests within the thirty minute time frame of a single forecast. We have designed CATS in a modular way to enable future integration of other countries' APIs in a straightforward manner. However, to date, we are unaware of any publicly accessible forecasts of carbon intensity for other regional, national or transnational electricity distribution networks.

With the carbon intensity forecast and duration of the proposed computation in hand, the next task is to locate the start time (within the valid forecast period) that minimises the integrated carbon intensity over a sliding window equal to the duration. All else being equal, this minimising start time is the time when the carbon cost of the proposed computation will be least. The difference in the integrated carbon footprint between an optimal start time and starting the calculation immediately is a measure of the potential benefits of timeshifting the computation. An illustration of this calculation is provided in Figure 1. Once the carbon intensity minimisation has been completed, CATS can optionally submit the computation to a queueing system or make a more detailed report on the climate impact of the proposed computation.

Submitting the computation to a queueing system is relatively straightforward and is most clearly illustrated by using the veritable `at` program available on most Linux and MacOS systems. The `at` program “queues jobs for later execution” and, assuming the user provides the command to run their computation and any necessary arguments (using the CATS `--command` option), it is relatively simple to schedule the computation to run at the optimal time by running `at` with the right arguments. We note that the options for the time syntax for `at` on different systems are mutually incompatible, so CATS restricts itself to the POSIX compatible time format. CATS also supports job submission to other queuing systems such as slurm. 

![illustration of the carbon intensity time series for (blue) with the predicted energy use for running a eight hour calculation now (red) or at a time that minimises the integrated carbon intensity (green).\label{fig:schedule}](fig1.png)

Providing further information about the carbon cost of the proposed computation improves the educational impact of CATS. This can be enabled with the `--footprint` command line option. This calculation follows that used by the Green Algorithms project [@Lannelongue21], which also provides some easy to understand “equivalent” statements to put these numbers in context. To provide this footprint information CATS must be configured with information about the hardware (principally the per-core power consumption of the processors) via “profiles” in the configuration file. Different profiles can allow for different classes of computation (for example, one that only uses the CPU, or one that uses the CPU and an attached GPU). This information, together with the grid carbon intensity and job duration, allows the total power consumption of the computation to be estimated along with the implied CO$_2$ cost if it were to be run now, or if the start time were to be delayed to minimise the carbon intensity. In addition, this information can be included in graphical output.

# Limitations and future work

While by itself, CATS is unlikely to drastically reduce the carbon footprint of research computing, it addresses a "low-hangging fruit" of the issue and empowers researchers to adapt their practices. The approach is likely to work best on DRIs that are not fully utilised and where all users are willing to collaborate to move computation to times of lower carbon intensity. It is important to note that CATS does not account for the embodied costs of computer manufacture which, for laptops or desktop machines, can amount to 50-70% of their lifecycle carbon footprint [@Lannelongue_Vegad_Dorn_2024; @MacBookPro]. However, CATS is a relatively simple tool that can be used to encourage research groups to discuss the carbon cost of their computation, and is a useful test-bed for more complex approaches that may be applied on larger machines. To this end, we are investigating methods to make use of the same carbon intensity data used by CATS to allow batch queueing systems to include the target of minimising the climate cost of computation as part of the scheduling algorithm.

# Acknowledgments

We are grateful to the staff of the Software Sustainability Institute and the organizers of
Collaborations Workshop 2023 (CW23), who's efforts allowed us to enjoy the process of beginning the development of CATS as part of the CW23 Hack Day, and to others who contributed to the development via bug reports, questions, and the other contributions that help open source software evolve. This work has been supported by the Software Sustainability Institute EPSRC, BBSRC, ESRC, NERC, AHRC, STFC and MRC (EP/S021779/1) and UKRI (AH/Z000114/1) grants.

# References

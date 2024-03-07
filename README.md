# CATS: **C**limate-**A**ware **T**ask **S**cheduler

CATS is a **C**limate-**A**ware **T**ask **S**cheduler. It schedules cluster jobs to minimize predicted carbon intensity of running the process. It was created as part of the [2023 Collaborations Workshop](https://software.ac.uk/cw23).

![CATS](https://i.imgur.com/QvbPDm7.png)

The Climate-Aware Task Scheduler is a lightweight Python package designed to schedule tasks based on the estimated carbon intensity of the electricity grid at any given moment. This tool uses real-time carbon intensity data from the National Grid ESO via their API to estimate the carbon intensity of the electricity grid, and schedules tasks at times when the estimated carbon intensity is lowest. This helps to reduce the carbon emissions associated with running computationally intensive tasks, making it an ideal solution for environmentally conscious developers.

*Currently CATS only works in the UK. If you are aware of APIs for realtime grid carbon intensity data in other countries please open an issue and let us know.*

## Features

- Estimates the carbon intensity of the electricity grid in real-time
- Schedules tasks based on the estimated carbon intensity, minimizing carbon emissions
- Provides a simple and intuitive API for developers
- Lightweight and easy to integrate into existing workflows
- Supports Python 3.9+

## Installation

Install via `pip` as follows:

```bash
pip install git+https://github.com/GreenScheduler/cats
```

## Documentation

Full documentation is available at [greenscheduler.github.io/cats/](https://greenscheduler.github.io/cats/). The below sections
demonstrate some capability, for illustration, but please consult
the documentation for more details.

#### Basic example

You can run `cats` with:

```bash
cats -d <job_duration> --loc <postcode>
```

The postcode is optional, and can be pulled from the `config.yml` file or, if that is not present, inferred using the server IP address. Job duration is in minutes, specified as an integer.

The scheduler then calls a function that estimates the best time to start the job given predicted carbon intensity over the next 48 hours. The workflow is the same as for other popular schedulers. Switching to `cats` should be transparent to cluster users.

By default, the optimal time to start the job is shown in a human readable format. This information can be output in a machine readable format by passing `--format=json`. The date format in the machine readable output can be controlled using `--dateformat` which accepts a [strftime(3)](https://manpages.debian.org/stable/manpages-dev/strftime.3.en.html) format date.


#### Use with schedulers

You can use CATS with, for example, the ``at`` job scheduler by running:

```bash
cats -d 5 --loc OX1 --scheduler at --command 'ls'
```
This schedules a command (`ls`) that has an expected runtime less than 5 minutes using the at scheduler.

#### Console demonstration

![CATS animated usage example](cats.gif)

#### Displaying carbon footprint estimates

`cats` is able to provide an estimate for the carbon footprint
reduction resulting from delaying your job.  To enable the footprint
estimation, you must provide information about the machine in the form
of a YAML configuration file.  An example is given below:

```yaml
location: "EH8"
api: "carbonintensity.org.uk"
PUE: 1.20 # > 1
partitions:
  CPU_partition:
    type: CPU # CPU or GPU
    model: "Xeon Gold 6142"
    TDP: 9.4 # Thermal Design Power in W/core
  GPU_partition:
    type: GPU
    model: "NVIDIA A100-SXM-80GB GPUs"
    TDP: 300
    CPU_model: "AMD EPYC 7763"
    TDP_CPU: 4.4
```

Use the `--config` option to specify a path to the configuration
file. If no path is specified, `cats` looks for a file named
`config.yml` in the current directory.

Additionally, to obtain carbon footprints, job-specific information
must be provided to `cats` through the `--jobinfo` option.  The
example below demonstrates running `cats` with footprint estimation
for a job using 8GB of memory, 2 CPU cores and no GPU:

```bash
cats -d 120 --config .config/config.yml \
  --jobinfo cpus=2,gpus=0,memory=8,partition=CPU_partition
```

## Contributing

We welcome contributions from the community! If you find a bug or have an idea for a new feature, please open an issue on our GitHub repository or submit a pull request.

## License

[MIT License](https://github.com/GreenScheduler/cats/blob/main/LICENSE)

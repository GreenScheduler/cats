# CATS

**C**limate-**A**ware **T**ask **S**cheduler

CATS is a Climate-Aware Task Scheduler. It schedules cluster jobs to minimize predicted carbon intensity of running the process. It was created as part of the [2023 Collaborations Workshop](https://software.ac.uk/cw23). 

Currently CATS only works in the UK, if you are aware of APIs for realtime grid carbon intensity data in other countries please open an issue and let us know.

![CATS](https://i.imgur.com/QvbPDm7.png)

The Climate-Aware Task Scheduler is a lightweight Python package designed to schedule tasks based on the estimated carbon intensity of the electricity grid at any given moment. This tool uses real-time carbon intensity data from the National Grid ESO via their API to estimate the carbon intensity of the electricity grid, and schedules tasks at times when the estimated carbon intensity is lowest. This helps to reduce the carbon emissions associated with running computationally intensive tasks, making it an ideal solution for environmentally conscious developers.
***
## Features
- Estimates the carbon intensity of the electricity grid in real-time
- Schedules tasks based on the estimated carbon intensity, minimizing carbon emissions
- Provides a simple and intuitive API for developers
- Lightweight and easy to integrate into existing workflows
- Supports Python 3.9+
***
## Installation
Install via `pip` as follows:

```bash
pip install git+https://github.com/GreenScheduler/cats
```

***
## Quickstart

You can run `cats` with:

```bash
python -m cats -d <job_duration> --loc <postcode>
```

The postcode is optional, and can be pulled from the `config.yml` file or, if that is not present, inferred using the server IP address.

The scheduler then calls a function that estimates the best time to start the job given predicted carbon intensity over the next 48 hours. The workflow is the same as for other popular schedulers. Switching to `cats` should be transparent to cluster users.

It will display the time to start the job on standard out and optionally some information about the carbon intensity on standard error.

***
### Display carbon footprint estimates

Optionally, `cats` will soon be able to provide an estimate for the carbon footprint reduction resulting from delaying your job.  To enable the footprint estimation, you must provide information about the machine in the form of a YAML configuration file.  An example is given below:

```yaml
## ~~~ TO BE EDITED TO BE TAILORED TO THE CLUSTER ~~~
##
## Settings for fictive CW23
##
## Updated: 04/05/2023

---
cluster_name: "CW23"
postcode: "EH8 9BT"
PUE: 1.20 # > 1
partitions:
  CPU_partition:
    type: CPU # CPU or GPU
    model: "Xeon Gold 6142"
    TDP: 9.4 # in W, per core
  GPU_partition:
    type: GPU
    model: "NVIDIA A100-SXM-80GB GPUs" 
    TDP: 300 # from https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/PB-10577-001_v02.pdf
    CPU_model: "AMD EPYC 7763" 
    TDP_CPU: 4.4 # from https://www.amd.com/fr/products/cpu/amd-epyc-7763
```

Use the `--config` option to specify a path to the config file, relative to the current directory. If no path is specified, `cats` looks for a file named `config.yml` in the current directory.


Additionally, to obtain carbon footprints, job-specific information must be provided to `cats` through the `--jobinfo` option.  The example below demonstrates running `cats` with footprint estimation for a job using 8GB of memory, 2 CPU cores and no GPU:

```bash
cats -d 120 --config .config/config.yml \
  --jobinfo cpus=2,gpus=0,memory=8,partition=CPU_partition
```


***
### Using with the `at` scheduler

You can use cats with the `at` job scheduler by running:

```bash
command | at `python -m cats -d <job_duration> --loc <postcode>
```

## Contributing
We welcome contributions from the community! If you find a bug or have an idea for a new feature, please open an issue on our GitHub repository or submit a pull request.
***
## License

[MIT License](https://github.com/GreenScheduler/cats/blob/main/LICENSE)

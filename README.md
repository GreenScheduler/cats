# CATS: **C**limate-**A**ware **T**ask **S**cheduler

CATS is a **C**limate-**A**ware **T**ask **S**cheduler. It schedules cluster jobs to minimize predicted carbon intensity of running the process. It was created as part of the [2023 Collaborations Workshop](https://software.ac.uk/cw23).

![CATS](https://i.imgur.com/QvbPDm7.png)

The Climate-Aware Task Scheduler is a lightweight Python package designed to schedule tasks based on the estimated carbon intensity of the electricity grid at any given moment. This tool uses real-time carbon intensity data from the National Grid ESO via their API to estimate the carbon intensity of the electricity grid, and schedules tasks at times when the estimated carbon intensity is lowest. This helps to reduce the carbon emissions associated with running computationally intensive tasks, making it an ideal solution for environmentally conscious developers.

*Currently CATS only works in the UK. If you are aware of APIs for realtime grid carbon intensity data in other countries please open an issue and let us know.*

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

## Documentation

Full documentation is available at LINK-PENDING. The below sections
demonstrate some capability, for illustration, but please consult
the documentation for more details.

#### Basic example

You can run `cats` with:

```bash
python -m cats -d <job_duration> --loc <postcode>
```

The postcode is optional, and can be pulled from the `config.yml` file or, if that is not present, inferred using the server IP address. Job duration is in minutes, specified as an integer.

The scheduler then calls a function that estimates the best time to start the job given predicted carbon intensity over the next 48 hours. The workflow is the same as for other popular schedulers. Switching to `cats` should be transparent to cluster users.

It will display the time to start the job on standard out and optionally some information about the carbon intensity on standard error.


#### Use with schedulers

You can use CATS with, for example, the ``at`` job scheduler by running:

```bash
ls | at -t `python -m cats -d 5 --loc OX1`
```

#### Console demonstration

![CATS animated usage example](cats.gif)

***

## Contributing

We welcome contributions from the community! If you find a bug or have an idea for a new feature, please open an issue on our GitHub repository or submit a pull request.

***

## License

[MIT License](https://github.com/GreenScheduler/cats/blob/main/LICENSE)

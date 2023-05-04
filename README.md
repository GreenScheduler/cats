# CATS

**C**limate **A**ware **T**ask **S**cheduler

CATS is a Climate Aware Task Scheduler. It schedules cluster jobs to minimize predicted carbon intensity of running the process. It was created as part of the [2023 Collaborations Workshop](https://software.ac.uk/cw23).

![CATS](https://i.imgur.com/QvbPDm7.png)


The Climate Aware Task Scheduler is a lightweight Python package designed to schedule tasks based on the estimated carbon intensity of the electricity grid at any given moment. This tool uses real-time carbon intensity data from the National Grid ESO via their API to estimate the carbon intensity of the electricity grid, and schedules tasks at times when the estimated carbon intensity is lowest. This helps to reduce the carbon emissions associated with running computationally intensive tasks, making it an ideal solution for environmentally conscious developers.
***
## Features
- Estimates the carbon intensity of the electricity grid in real-time
- Schedules tasks based on the estimated carbon intensity, minimizing carbon emissions
- Provides a simple and intuitive API for developers
- Lightweight and easy to integrate into existing workflows
- Supports Python 3.9+
***
## Installation
Clone the repository

```shell
pip install git+https://github.com/GreenScheduler/cats
```

***
## Quickstart
```sh
cats  -d/--duration job_duration --loc postcode
```
The postcode is optional, and can be pulled from the `config.yml` file or, if that is not present, inferred using the server IP address.

The scheduler then calls a function that estimates the best time to start the job given predicted carbon intensity over the next 48 hours. The workflow is the same as for other popular schedulers. Switching to `cats` should be transparent to cluster users.
***
## Contributing
We welcome contributions from the community! If you find a bug or have an idea for a new feature, please open an issue on our GitHub repository or submit a pull request.
***
## License

[MIT License](https://github.com/GreenScheduler/cats/blob/main/LICENSE)

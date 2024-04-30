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

Documentation is available at [greenscheduler.github.io/cats/](https://greenscheduler.github.io/cats/).

We recommend the
[quickstart](https://greenscheduler.github.io/cats/quickstart.html#basic-usage)
if you are new to CATS. CATS can optionally [display carbon footprint
savings](https://greenscheduler.github.io/cats/quickstart.html#displaying-carbon-footprint-estimates)
using a [configuration file](cats/config.yml).

### Console demonstration
CATS predicting optimal start time for the `ls` command in the `OX1` postcode:

![CATS animated usage example](cats.gif)

## Contributing

We welcome contributions from the community! If you find a bug or have an idea for a new feature, please open an issue on our GitHub repository or submit a pull request.

## License

[MIT License](https://github.com/GreenScheduler/cats/blob/main/LICENSE)

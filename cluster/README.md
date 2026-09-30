# Cluster tests

This folder contains scripts to setup an ephemeral SLURM cluster to test
cats in a more realistic setting than the current integration tests that
use mocking. The setup builds upon work from upstream
https://github.com/giovtorres/slurm-docker-cluster with a patched
Dockerfile that installs jq and uv to make CATS installation easier. Our
patches are maintained at
https://github.com/GreenScheduler/slurm-docker-cluster.

## Pre-requisites

Currently slurm-docker-cluster is only built against linux/amd64 so you
will need to be on a 64-bit machine if you want to test this locally. You
will also need docker installed.

## Setup

Clone this repository (GreenScheduler/cats) and then run

```shell
./cluster/start.sh
```

to fetch the `ghcr.io/greenscheduler/slurm-docker-cluster:latest` image
and start the cluster. You can now install cats locally from the current checkout:

```shell
./cluster/install_cats.sh
```

Once the cluster is built and running, then you can run the following to get
access to the control node:

```shell
docker exec -it slurmctld bash
```

The `catsd` Compose service runs the dynamic scheduler in the background. Submit
a job with `--dynamic` to let it re-evaluate the forecast hourly and update the
start time of that job while it remains pending:

```shell
cats -d 5 --loc RG1 --scheduler sbatch --command 'sleep 120' --dynamic
```

The daemon only changes pending jobs marked dynamic. Follow its logs with:

```shell
docker logs -f catsd
```

## Tests

An automated testing script is supplied which shows programmatic interaction
with the slurm cluster. Currently cats schedules a short job, and the slurm
`scontrol` output is checked to see that the job was scheduled correctly. To
run the test:

```shell
./cluster/tests.sh
```

# Cluster tests

This folder contains scripts to setup an ephemeral SLURM cluster to test cats
in a more realistic setting than the current integration tests that use
macking. The setup builds upon work from upstream
https://github.com/giovtorres/slurm-docker-cluster with a patched
[Dockerfile](Dockerfile) that installs the latest release of CATS and makes it
available in the cluster.

## Setup

Clone this repository (GreenScheduler/cats) and then run

```shell
./cats/clone.sh
./cats/build.sh
```
to clone the slurm-docker-cluster repo, patch the Dockerfile to install CATS,
build and start the cluster. Note that this requires `docker` and `docker
compose` to be present. Currently this compiles a specific SLURM version, so
this may take a while on older computers. When developing locally, you should
only need to do this once, unless you update the Dockerfile.

Once the cluster is built and running, then you can run the following to get
access to the control node:

```shell
docker exec -it slurmctld bash
```

For more information about slurm-docker-cluster, consult the upstream
repository.

## Tests

An automated testing script is supplied which shows programmatic interaction
with the slurm cluster. Currently cats schedules a short job, and the slurm
`scontrol` output is checked to see that the job was scheduled correctly. To
run the test:

```shell
./cluster/tests.sh
```

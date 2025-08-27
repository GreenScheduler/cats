#!/bin/bash
# Cleans up resources and shuts down containers, useful for local development of slurm-docker-cluster
set -eou pipefail

docker compose down
if [ -d slurm-docker-cluster ]; then
    rm -r slurm-docker-cluster
fi

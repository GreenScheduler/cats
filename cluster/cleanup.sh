#!/bin/bash
# Cleans up resources and shuts down containers, useful for local development of slurm-docker-cluster
set -eou pipefail

pushd cluster
docker compose down
popd

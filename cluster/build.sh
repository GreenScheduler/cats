#!/bin/bash
# Builds slurm-docker-cluster with patched Dockerfile that installs cats
set -eou pipefail
pushd slurm-docker-cluster
echo :: Patching Dockerfile with version that installs cats
cp ../cluster/Dockerfile .
docker compose build
docker compose up -d
popd

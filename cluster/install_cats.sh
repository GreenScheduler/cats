#!/usr/bin/env bash
# Install cats on the slurm custer
# This relies on a cluster already setup and running, if not run
#   ./cluster/start.sh
set -eou pipefail

docker exec slurmctld mkdir /tmp/cats
for file in pyproject.toml ./cats; do
  docker cp "$file" slurmctld:/tmp/cats
done
docker exec slurmctld uv tool install /tmp/cats
docker exec slurmctld cp /root/.local/bin/cats /usr/local/bin/cats

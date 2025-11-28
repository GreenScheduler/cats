#!/bin/bash
# Starts cluster
set -eou pipefail
pushd cluster
docker compose pull
docker compose up -d
popd

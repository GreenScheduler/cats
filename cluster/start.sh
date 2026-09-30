#!/bin/bash
# Starts cluster
set -eou pipefail
pushd cluster
docker compose build --pull
docker compose up -d
popd

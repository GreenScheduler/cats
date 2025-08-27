#!/bin/bash
set -eou pipefail
git clone https://github.com/giovtorres/slurm-docker-cluster
pushd slurm-docker-cluster
git checkout c9aa93c080567121c6b28913152a1cd696465985
popd

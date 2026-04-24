#!/usr/bin/env bash
# Run tests to check if slurm picks up begin time set by CATS
# This relies on a cluster already setup and running, if not run
#   ./cluster/start.sh
set -eou pipefail

# Step a) Run cats inside the slurmctld container and extract start time
raw_output=$(docker exec -i slurmctld \
  cats -d 5 --loc RG1 --scheduler=sbatch --command='ls' --format=json | \
  awk 'BEGIN{found=0} {
      if(!found){
          i=index($0,"{");
          if(i){ print substr($0,i); found=1 }
      } else { print }
  }')
job_id=$(echo "$raw_output" | grep ^Submitted | awk '{print $4}')
echo "Detected job submission ID: $job_id"
raw_json=$(echo "$raw_output" | grep -v ^Submitted)
raw_start=$(printf '%s\n' "$raw_json" | jq -r '.carbonIntensityOptimal.start')

# Replace seconds with 00 (truncate last 6 chars and add "00")
# Example: 2025-08-28T12:43:30.156434+00:00 -> 2025-08-28T12:43:00
scheduled_start=$(echo "$raw_start" | sed -E 's/:[0-9]{2}\..*/:00/')

echo "Expected scheduled start time: $scheduled_start"

# Step b) Fetch job details
job_output=$(docker exec -i slurmctld scontrol show job "$job_id")

# Check condition 1: job is pending for BeginTime
if (! echo "$job_output" | grep -q "JobState=PENDING Reason=BeginTime Dependency=(null)") && \
  (! echo "$job_output" | grep -q "JobState=RUNNING Reason=None"); then
  echo "❌ Job state/Reason is not correct, expected one of PENDING/BeginTime or RUNNING/None"
  echo "$job_output"
  exit 1
fi

# Check condition 2: start time matches
if ! echo "$job_output" | grep -q "StartTime=$scheduled_start"; then
  echo "❌ Start time does not match expected!"
  echo "Expected: StartTime=$scheduled_start"
  echo "Actual output:"
  echo "$job_output"
  exit 1
fi

echo "✅ Job is correctly delayed until $scheduled_start"

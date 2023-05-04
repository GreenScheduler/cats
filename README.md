# CATS

CATS is a Climate Aware Task Scheduler. It schedules cluster jobs to minimize predicted carbon intensity of running the process. It was created as part of the [2023 Collaborations Workshop](https://software.ac.uk/cw23).

# The procedure

The user submits a job with the command

```sh
cats job_name -d/--duration job_duration --loc postcode
```

The scheduler then calls a function that estimates the best time to start the job given predicted carbon intensity over the next 48 hours. The workflow is the same as for other popular schedulers. Switching to `cats` should be transparent to cluster users.

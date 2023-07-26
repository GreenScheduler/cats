import re
import sys

def validate_jobinfo(jobinfo: str, expected_partition_names):
    """Parses a string of job info keys in the form

    partition=CPU_partition,memory=8,ncpus=8,ngpus=0

    and checks all required info keys are present and of the right type.

    Returns
    -------

    info: dict
        A dictionary mapping info key to their specified values
    """

    expected_info_keys = (
        "partition",
        "memory",
        "cpus",
        "gpus",
    )
    info = dict([match.groups() for match in re.finditer(r"(\w+)=(\w+)", jobinfo)])

    # Check if some information is missing
    if missing_keys := set(expected_info_keys) - set(info.keys()):
        sys.stderr.write(f"ERROR: Missing job info keys: {missing_keys}")
        return {}

    # Validate partition value
    if info["partition"] not in expected_partition_names:
        sys.stderr.write(f"ERROR: job info key 'partition' should be one of {expected_partition_names}. Typo?\n")
        return {}

    # check that `cpus`, `gpus` and `memory` are numeric and convert to int
    for key in [k for k in info if k != "partition"]:
        try:
            info[key] = int(info[key])
        except ValueError:
            sys.stderr.write(f"ERROR: job info key {key} should be numeric\n")
            return {}

    return info

def validate_duration(duration):
    # make sure it can be converted to integer
    try:
        duration_int = int(duration)
    except ValueError:
        raise ValueError("--duration needs to be an integer or float (number of minutes)")
    # make sure it's positive
    if duration_int <= 0:
        raise ValueError("--duration needs to be positive (number of minutes)")

    return duration_int

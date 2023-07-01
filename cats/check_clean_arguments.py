import re

def validate_jobinfo(jobinfo: str):
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
    info = {
        k: v
        for k, v in [match.groups() for match in re.finditer(r"(\w+)=(\w+)", jobinfo)]
    }
    missing_keys = set(expected_info_keys) - set(info.keys())
    if missing_keys:
        print(f"ERROR: Missing job info keys: {missing_keys}")
        return {}
    expected_partition_values = ("CPU_partition", "GPU_partition")
    if info["partition"] not in expected_partition_values:
        msg = (
            "ERROR: job info key 'partition' should be "
            f"one of {expected_partition_values}. Typo?"
        )
        print(msg)
        return {}
    for key in [k for k in info.keys() if k != "partition"]:
        try:
            info[key] = int(info[key])
        except ValueError:
            print(f"ERROR: job info key {key} should be numeric")
            return {}
    return info
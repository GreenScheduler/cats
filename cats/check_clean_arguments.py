import re
import sys
from datetime import timedelta

class sanityChecks_arguments():
    def __init__(self):
        pass

    def validate_jobinfo(self, jobinfo: str):
        '''
        Parses a string of job info keys in the form

        partition=CPU_partition,memory=8,cpus=8,gpus=0

        and checks all required info keys are present and of the right type.
        :param jobinfo: [str]
        :return: [dict] A dictionary mapping info key to their specified values
        '''

        expected_info_keys = (
            "partition",
            "memory",
            "cpus",
            "gpus",
        )
        info = dict([match.groups() for match in re.finditer(r"(\w+)=(\w+)", jobinfo)])

        # Check if some information is missing
        missing_keys = set(expected_info_keys) - set(info.keys())
        if missing_keys:
            sys.stderr.write(f"ERROR: Missing job info keys: {missing_keys}, energy usage cannot be estimated.\n")
            return None

        # Validate partition value
        expected_partition_values = self.config['partitions'].keys()
        if info["partition"] not in expected_partition_values:
            sys.stderr.write(
                "ERROR: job info key 'partition' should be "
                f"one of {expected_partition_values}. Typo?"
            )
            return None

        # check that `cpus`, `gpus` and `memory` are numeric and convert to int
        for key in [k for k in info if k != "partition"]:
            try:
                info[key] = int(info[key])
            except ValueError:
                sys.stderr.write(f"ERROR: job info key {key} should be numeric")
                return None

        return info

    def validate_duration(self, duration):
        # make sure it is can be converted to integer
        try:
            duration_int = int(duration)
        except ValueError:
            raise ValueError("--duration needs to be an integer or float (number of minutes)")
        # make sure size is positive
        if duration_int <= 0:
            raise ValueError("--duration needs to be positive (number of minutes)")

        return timedelta(minutes=duration_int)

    def validate_location(self, location, choice_CI_API):
        if choice_CI_API == 'carbonintensity.org.uk':
            # in case the long format of the postcode is provided:
            loc_cleaned = location.split()[0]

            # check that it's between 2 and 4 characters long
            if (len(loc_cleaned) < 2) or (len(loc_cleaned) > 4):
                raise ValueError(f"{location} is an invalid UK postcode. Only the first part of the postcode is expected (e.g. M15).")

        else:
            loc_cleaned = location

        return loc_cleaned
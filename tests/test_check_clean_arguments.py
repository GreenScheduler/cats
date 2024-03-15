import pytest

from cats.check_clean_arguments import validate_jobinfo

# This is usually read from a config.yml file under the 'partitions' key
PARTITIONS = ["CPU_partition", "GPU_partition"]


def test_validate_jobinfo_ok():
    assert validate_jobinfo(
        "cpus=2,gpus=0,memory=8,partition=CPU_partition", PARTITIONS
    ) == dict(cpus=2, gpus=0, memory=8, partition="CPU_partition")


@pytest.mark.parametrize(
    "jobinfo",
    [
        "cpus=2.5,gpus=1,memory=8,partition=CPU_partition",  # floating CPUs
        "cpus=2,gpus=-1,memory=8,partition=CPU_partition",  # negative integer
        "cpus=2",  # missing keys
        "cpus=2,gpus=2,memory=8,partition=one",  # unknown partition
    ],
)
def test_validate_jobinfo_notok(jobinfo):
    assert validate_jobinfo(jobinfo, PARTITIONS) is None

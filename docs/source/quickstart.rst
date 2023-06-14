.. _quickstart:

Quickstart
==========

Basic usage
-----------

You can run CATS with:

.. code-block:: console
   :caption: *A basic command to run CATS when a job duration and postcode
              are provided.*

   $ python -m cats -d <job_duration> --loc <postcode>

The ``postcode`` is optional, and can be pulled from the ``config.yml`` file
or, if that is not present, inferred using the server IP address.

The ``job_duration`` is in minutes, specified as an integer.

The scheduler then calls a function that estimates the best time to start
the job given predicted carbon intensity over the next 48 hours. The
workflow is the same as for other popular schedulers. Switching to CATS
should be transparent to cluster users.

It will display the time to start the job on standard out and optionally
some information about the carbon intensity on standard error.


Displaying carbon footprint estimates
-------------------------------------

Optionally, CATS will soon be able to provide an estimate for the
carbon footprint reduction resulting from delaying your job. To enable
the footprint estimation, you must provide information about the
machine in the form of a YAML configuration file. An example is
given below:

.. code-block:: yaml
   :caption: *An example provision of machine information by YAML file
             to enable estimation of the carbon footprint reduction.*

   ## ~~~ TO BE EDITED TO BE TAILORED TO THE CLUSTER ~~~
   ##
   ## Settings for fictive CW23
   ##
   ## Updated: 04/05/2023

   ---
   cluster_name: "CW23"
   postcode: "EH8 9BT"
   PUE: 1.20 # > 1
   partitions:
     CPU_partition:
       type: CPU # CPU or GPU
       model: "Xeon Gold 6142"
       TDP: 9.4 # in W, per core
     GPU_partition:
       type: GPU
       model: "NVIDIA A100-SXM-80GB GPUs"
       TDP: 300 # from https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/PB-10577-001_v02.pdf
       CPU_model: "AMD EPYC 7763"
       TDP_CPU: 4.4 # from https://www.amd.com/fr/products/cpu/amd-epyc-7763


Use the ``--config`` option to specify a path to the config file, relative
to the current directory. If no path is specified, CATS looks for a
file named ``config.yml`` in the current directory.

Additionally, to obtain carbon footprints, job-specific information
must be provided to CATS through the ``--jobinfo`` option. The example
below demonstrates running CATS with footprint estimation for a job using
8GB of memory, 2 CPU cores and no GPU:

.. code-block:: console
   :caption: *An example run command showing provision of job information.*

   $ cats -d 120 --config .config/config.yml --jobinfo cpus=2,gpus=0,memory=8,partition=CPU_partition

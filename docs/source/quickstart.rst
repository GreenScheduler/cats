.. _quickstart:

Quickstart
==========

Basic usage
-----------

You can run CATS with:

.. code-block:: console
   :caption: *A basic command to run CATS when a job duration and postcode
              are provided.*

   $ cats --duration 480 --location "EH8"

The ``--postcode`` option is optional, and can be pulled from a
configuration file (see :ref:`configuration-file`), or inferred using
the server's IP address.

The ``--duration`` option indicates the expected job duration in
minutes.

The scheduler then calls a function that estimates the best time to start
the job given predicted carbon intensity over the next 48 hours. The
workflow is the same as for other popular schedulers. Switching to CATS
should be transparent to cluster users.

It will display the time to start the job on standard out and optionally
some information about the carbon intensity on standard error.

.. _configuration-file:

Using a configuration file
--------------------------

Information about location can be provided by a configuration file
instead of a command line arguments to the ``cats`` command.

.. code-block:: yaml

   location: "EH8"

Use the ``--config`` option to specify a path to the configuration
file, relative to the current directory.

In case of a missing location command line argument, ``cats`` looks
for a file named ``config.yaml`` in the current directory.

.. code-block:: shell

   #  Override duration value at the command line
   cats --config /path/to/config.yaml --location "OX1"

.. code-block:: shell

   #  location information is assumed to be provided in
   #  ./config.yaml.  If not, 'cats' errors out.
   cats --duration 480


Displaying carbon footprint estimates
-------------------------------------

CATS is able to provide an estimate for the carbon footprint reduction
resulting from delaying your job. To enable the footprint estimation,
you must provide the ``--footprint`` option, the memory consumption in GB
and a hardware profile:

.. code-block:: shell

   cats --duration 480 --location "EH8" --footprint --memory 8 --profile <my_profile>

The ``--profile`` option specifies information power consumption and
quantity of hardware the job using. This information is provided by
adding a section ``profiles`` to the :ref:`cats YAML configuration
file <configuration-file>`.

You can define an arbitraty number of profiles as subsection of the
top-level ``profiles`` section:

.. code-block:: yaml
   :caption: *An example provision of machine information by YAML file
             to enable estimation of the carbon footprint reduction.*

   profiles:
     my_cpu_only_profile:
       cpu:
         model: "Xeon Gold 6142"
         power: 9.4 # in W, per core
         nunits: 2
     my_gpu_profile:
       gpu:
         model: "NVIDIA A100-SXM-80GB GPUs"
         power: 300
         nunits: 2
       cpu:
         model: "AMD EPYC 7763"
         power: 4.4
         nunits: 1

The name of the profile section is arbitrary, but each profile section
*must* contain one ``cpu`` section, or one ``gpu`` section, or both.
Each hardware type (``cpu`` or ``gpu``) section *must* contain the
``power`` (in Watts, for one unit) and ``nunits`` sections. The ``model`` section is optional,
meant for documentation.

When running ``cats``, you can specify which profile to use for carbon
footprint estimation with the ``--profile`` option:

.. code-block:: shell

   cats --duration 480 --location "EH8" --footprint --memory 6.7 --profile my_gpu_profile

The default number of units specified for a profile can be overidden
at the command line:

.. code-block:: shell

   cats --duration 480 --location "EH8" --footprint --memory 16 \
        --profile my_gpu_profile --gpu 4 --cpu 1

.. warning::
   The ``--profile`` option is optional. Is not provided, ``cats`` uses the
   first profile defined in the configuration file as the default
   profile.

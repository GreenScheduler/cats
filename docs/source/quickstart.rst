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

The ``--location`` option is optional, and can be pulled from a
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
first in the ``CATS_CONFIG_FILE`` environment variable and if that
is not set it looks for a file named ``config.yml``
in the current directory.

.. code-block:: shell

   #  Override duration value at the command line
   cats --config /path/to/config.y(a)ml --location "OX1"

When ``--duration`` information is not provided via the option, and
location information is not provided in the YAML configuration file
specified or detected, CATS will try to estimate location from the
machine IP address:

.. code-block:: console

   $ cats --duration 480
   WARNING:root:config file not found
   WARNING:root:Unspecified carbon intensity forecast service, using carbonintensity.org.uk
   WARNING:root:location not provided. Estimating location from IP address: RG2.
   Best job start time 2024-08-22 07:30:49.800951+01:00
   Carbon intensity if job started now       = 117.95 gCO2eq/kWh
   Carbon intensity at optimal time          = 60.93 gCO2eq/kWh

Use --format=json to get this in machine readable format

.. code-block::console

   # location information is provided by the file
   # specified in $CATS_CONFIG_FILE
   # If not, it looks for ./config.yml
   # otherwise 'cats' errors out.
   export CATS_CONFIG_FILE=/path/to/config.yml
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

You can define an arbitrary number of profiles as subsection of the
top-level ``profiles`` section:

.. literalinclude :: ../../cats/config.yml
   :language: yaml
   :caption: *An example provision of machine information by YAML file
             to enable estimation of the carbon footprint reduction.*

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
   The ``--profile`` option is optional. If not provided, ``cats`` uses the
   first profile defined in the configuration file as the default
   profile.

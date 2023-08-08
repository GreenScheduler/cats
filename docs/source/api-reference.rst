.. _api-reference:

API Reference
=============

This is a reference covering **the Python modules and objects across
the CATS codebase**. For the interface for the *command-line*, which is
likely to be more relevant to *users* (rather than developers) of CATS,
please see :ref:`cli-reference`.

Modules
-------

``cats.__init__``
^^^^^^^^^^^^^^^^^

.. automodule:: cats.__init__
    :members:

``cats.__main__``
^^^^^^^^^^^^^^^^^

.. automodule:: cats.__main__
    :members:

``cats.CI_api_interface``
^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.CI_api_interface
    :members:

``cats.CI_api_query``
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.CI_api_query
    :members:

``cats.carbonFootprint``
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.carbonFootprint
    :members:

``cats.forecast``
^^^^^^^^^^^^^^^^^

.. automodule:: cats.forecast
    :members:


``cats.optimise_starttime``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.optimise_starttime
    :members:

Python objects
--------------


In ``cats.__init__``
^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.__init__.parse_arguments
   cats.__init__.main


In ``cats.__main__``
^^^^^^^^^^^^^^^^^^^^

n/a


In ``cats.CI_api_interface``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.CI_api_interface.ciuk_request_url
   cats.CI_api_interface.ciuk_parse_response_data

Variables and constants
"""""""""""""""""""""""

.. autosummary::

   cats.CI_api_interface.APIInterface
   cats.CI_api_interface.API_interfaces

In ``cats.CI_api_query``
^^^^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.CI_api_query.get_CI_forecast


In ``cats.carbonFootprint``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Classes
"""""""

.. autosummary::

   cats.carbonFootprint.greenAlgorithmsCalculator

Variables and constants
"""""""""""""""""""""""

.. autosummary::

   cats.carbonFootprint.Estimates


In ``cats.forecast``
^^^^^^^^^^^^^^^^^^^^

Classes
"""""""

.. autosummary::

   cats.forecast.CarbonIntensityPointEstimate
   cats.forecast.CarbonIntensityAverageEstimate
   cats.forecast.WindowedForecast

In ``cats.optimise_starttime``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.optimise_starttime.get_avg_estimates

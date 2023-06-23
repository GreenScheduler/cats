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

``cats.api_interface``
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.api_interface
    :members:

``cats.api_query``
^^^^^^^^^^^^^^^^^^

.. automodule:: cats.api_query
    :members:

``cats.carbonFootprint``
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.carbonFootprint
    :members:

``cats.forecast``
^^^^^^^^^^^^^^^^^

.. automodule:: cats.forecast
    :members:

``cats.parsedata``
^^^^^^^^^^^^^^^^^^

.. automodule:: cats.parsedata
    :members:

``cats.timeseries_conversion``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: cats.timeseries_conversion
    :members:


Python objects
--------------




In ``cats.__init__``
^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.__init__.findtime
   cats.__init__.parse_arguments
   cats.__init__.validate_jobinfo
   cats.__init__.main


In ``cats.__main__``
^^^^^^^^^^^^^^^^^^^^

n/a


In ``cats.api_interface``
^^^^^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.api_interface.ciuk_request_url
   cats.api_interface.ciuk_parse_response_data

Variables and constants
"""""""""""""""""""""""

.. autosummary::

   cats.api_interface.APIInterface
   cats.api_interface.API_interfaces

In ``cats.api_query``
^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.api_query.get_tuple


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


In ``cats.parsedata``
^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.parsedata.avg_carbon_intensity


In ``cats.timeseries_conversion``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functions
"""""""""

.. autosummary::

   cats.timeseries_conversion.check_duration
   cats.timeseries_conversion.get_lowest_carbon_intensity

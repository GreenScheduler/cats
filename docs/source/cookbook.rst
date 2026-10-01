.. _cookbook:

Cookbook
========

Recipes for common things you might want to do with CATS beyond the default carbon-aware scheduling: choosing a different goal such as price or water use, balancing several goals at once, and keeping your costs under control. The outputs shown are examples from one run and will differ on yours.

Run ``cats --list-providers`` to see which data sources (``--api``) and goals (``--metric``) are available, and ``cats --list-locations`` to see the valid ``--location`` codes for each.

Run a job when the grid is cleanest
-----------------------------------

This is the default. Give CATS the duration of your job in minutes and your location.

.. code-block:: console

   $ cats --duration 60 --location OX1

   Best job start time                 = 2026-09-30 14:40:20
   Carbon intensity if job started now = 66.13 gCO2eq/kWh
   Carbon intensity at optimal time    = 63.70 gCO2eq/kWh
   Price if job started now            = 153.19 GBP/MWh
   Price at chosen start time          = 218.16 GBP/MWh (+ 64.97)

Whenever electricity price data is available for your location, CATS also tells you what the chosen start time costs compared with starting now. See :ref:`cookbook-price-constraint` if you want to limit that.

Run a job when electricity is cheapest
--------------------------------------

Use ``--metric price`` to minimise day-ahead electricity price instead of carbon intensity. In Great Britain the ``octopus.energy`` API takes a region letter as the location (``C`` is London).

.. code-block:: console

   $ cats --duration 60 --location C --api octopus.energy

   Best job start time                            = 2026-09-30 12:40:21
   Day-ahead electricity price if job started now = 144.31 GBP/MWh
   Day-ahead electricity price at optimal time    = 144.31 GBP/MWh

In continental Europe use ``energy-charts.info`` with a bidding zone or country code.

.. code-block:: console

   $ cats --duration 60 --location ES --api energy-charts.info --metric price

   Best job start time                            = 2026-10-01 12:40:22
   Day-ahead electricity price if job started now = 97.55 EUR/MWh
   Day-ahead electricity price at optimal time    = 39.11 EUR/MWh

Run a job when the most renewable energy is available
-----------------------------------------------------

Use ``--metric renewables``. CATS reports the non-renewable share, so lower is still better.

.. code-block:: console

   $ cats --duration 60 --location OX1 --metric renewables

   Best job start time                    = 2026-09-30 12:40:21
   Non-renewable share if job started now = 23.51 %
   Non-renewable share at optimal time    = 23.51 %

Minimise water use or environmental impact
------------------------------------------

The ``wattnet.eu`` API (which needs a free registration, see :ref:`quickstart`) offers several environmental goals for European zones: ``carbon``, ``water``, ``water_stress`` (water use weighted by local scarcity) and ``environmental_score``.

.. code-block:: console

   $ cats --duration 60 --location DE --api wattnet.eu --metric water

   Water footprint if job started now = 11.89 L/kWh
   Water footprint at optimal time    = 11.80 L/kWh
   Price if job started now           = 26.88 EUR/MWh
   Price at chosen start time         = 156.99 EUR/MWh (+ 130.11)

Note that a price comparison is only shown when price data covers both the start time you would get now and the chosen one. Price forecasts usually cover a shorter period than the environmental forecasts, so it is sometimes left out.

``environmental_score`` is wattnet.eu's own combination of the carbon, water and water stress measures. Use it instead of combining those three yourself.

.. _cookbook-composite:

Balance several goals at once
-----------------------------

Use ``--api composite`` to trade off several goals, giving each a weight with ``--signal NAME=WEIGHT``. Weights do not need to add up to 1. CATS works out whether your location is a GB postcode or a wattnet.eu zone and picks the right data source for each goal.

.. code-block:: console

   $ cats --duration 60 --location OX1 --api composite --signal carbon=0.5 --signal renewables=0.5

With no ``--signal`` options, every goal that needs no registration and is available for your location is weighted equally.

.. code-block:: console

   $ cats --duration 60 --location OX1 --api composite

   Composite score (carbon=0.33, price=0.33, renewables=0.33) if job started now = 0.04 0-1, lower=better
   Composite score (carbon=0.33, price=0.33, renewables=0.33) at optimal time    = 0.04 0-1, lower=better

The score is a number between 0 and 1 where lower is better, so it is only meaningful for comparing start times in the same run.

Because ``environmental_score`` already includes carbon, water and water stress, combine it only with goals it does not cover, such as ``price`` and ``renewables``.

.. code-block:: console

   $ cats --duration 60 --location DE --api composite --signal environmental_score=0.34 --signal price=0.33 --signal renewables=0.33

Some goals are not available everywhere. If you ask for one that has no data for your location CATS tells you which are available, and an unknown goal name lists the valid ones.

.. code-block:: console

   $ cats --duration 60 --location XK --api composite --signal price=1.0
   Invalid location: Signal(s) ['price'] have no data source for location 'XK' (wattnet_zone); available here: ['carbon', 'environmental_score', 'water', 'water_stress']

.. _cookbook-price-constraint:

Keep your costs under control
-----------------------------

The cleanest time to run is not always the cheapest, and it can cost more than starting now.

.. code-block:: console

   $ cats --duration 60 --location OX1

   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 63.71 gCO2eq/kWh
   Price if job started now            = 153.39 GBP/MWh
   Price at chosen start time          = 219.20 GBP/MWh (+ 65.81)

Rather than mixing price into a composite score, where it could take over the decision, you can set a price limit. CATS then picks the best start time among those within the limit. Use ``--max-price-increase-pct`` to limit how much more than starting now you are willing to pay, with ``0`` meaning never more.

.. code-block:: console

   $ cats --duration 60 --location OX1 --max-price-increase-pct 0

   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 66.10 gCO2eq/kWh
   Price if job started now            = 153.39 GBP/MWh
   Price at chosen start time          = 153.39 GBP/MWh (- 0.00)

Or use ``--max-price`` to set an absolute limit in the unit of your location (GBP/MWh for a GB postcode, EUR/MWh in Europe). A limit above the price of the best start time changes nothing, and a tighter one forces a different choice.

.. code-block:: console

   $ cats --duration 60 --location OX1 --max-price 160

   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 66.10 gCO2eq/kWh
   Price at chosen start time          = 153.40 GBP/MWh (- 0.00)

The two options cannot be used together. If no start time satisfies the limit, or the location has no price data, CATS stops with an error instead of ignoring the limit.

.. code-block:: console

   $ cats --duration 60 --location OX1 --max-price 1
   Price constraint not satisfiable: No candidate start time both falls within price data's forecast horizon and satisfies the price constraint (cap=1.00); try relaxing --max-price/--max-price-increase-pct or removing it.

Options at a glance
-------------------

======================================  ===============================================================
Option                                  What it does
======================================  ===============================================================
``--metric NAME``                       What to minimise, for APIs that offer more than one goal
``--signal NAME=WEIGHT``                Repeatable. Goal and weight to combine with ``--api composite``
``--max-price N``                       Absolute price limit, in the unit of your location
``--max-price-increase-pct N``          Price limit relative to the price of starting now
``--list-providers``                    List the APIs and their goals, without needing ``--duration``
``--list-locations``                    List the valid ``--location`` codes of one API (or all),
                                        without needing ``--duration``
======================================  ===============================================================

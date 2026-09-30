.. _cookbook:

Cookbook
========

Worked examples of the provider/metric combinations, the ``composite``
provider, and the price constraint, with real CLI output from a run
against the live APIs on ``feature/price-providers``. The numbers are a
snapshot from one run and will differ on yours.

Single-metric providers
------------------------

Each portal is one provider class; the specific metric is chosen with
``--metric`` (or defaults to one).

.. code-block:: console
   :caption: *carbonintensity.org.uk's carbon metric (the default).*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk
   ...

   Best job start time                 = 2026-09-30 14:40:20
   Carbon intensity if job started now = 66.13 gCO2eq/kWh
   Carbon intensity at optimal time    = 63.70 gCO2eq/kWh
   Price if job started now            = 153.19 GBP/MWh
   Price at chosen start time          = 218.16 GBP/MWh (+ 64.97)

The price block appears automatically whenever there is price coverage
for the location, even without asking for any constraint; see
:ref:`cookbook-price-constraint` below.

.. code-block:: console
   :caption: *carbonintensity.org.uk's renewables metric.*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk --metric renewables
   ...

   Best job start time                    = 2026-09-30 12:40:21
   Non-renewable share if job started now = 23.51 %
   Non-renewable share at optimal time    = 23.51 %

.. code-block:: console
   :caption: *octopus.energy's price metric, for GB region letter C (London).*

   $ cats --duration 60 --location C --api octopus.energy
   ...

   Best job start time                            = 2026-09-30 12:40:21
   Day-ahead electricity price if job started now = 144.31 GBP/MWh
   Day-ahead electricity price at optimal time    = 144.31 GBP/MWh

No extra price block here: price is already the primary metric. The
location is a GB region letter (``C``), not a postcode.

.. code-block:: console
   :caption: *energy-charts.info's price metric, for Spain.*

   $ cats --duration 60 --location ES --api energy-charts.info --metric price
   ...

   Best job start time                            = 2026-10-01 12:40:22
   Day-ahead electricity price if job started now = 97.55 EUR/MWh
   Day-ahead electricity price at optimal time    = 39.11 EUR/MWh

.. code-block:: console
   :caption: *wattnet.eu's four metrics, same zone (DE).*

   $ cats --duration 60 --location DE --api wattnet.eu --metric carbon
   Carbon intensity if job started now = 176.68 gCO2/kWh
   Carbon intensity at optimal time     = 161.41 gCO2/kWh

   $ cats --duration 60 --location DE --api wattnet.eu --metric water
   Water footprint if job started now = 11.89 l/kWh
   Water footprint at optimal time    = 11.80 l/kWh
   Price if job started now           = 26.88 EUR/MWh
   Price at chosen start time         = 156.99 EUR/MWh (+ 130.11)

   $ cats --duration 60 --location DE --api wattnet.eu --metric water_stress
   Water stress if job started now = 0.02 stress-l/kWh
   Water stress at optimal time    = 0.01 stress-l/kWh

   $ cats --duration 60 --location DE --api wattnet.eu --metric environmental_score
   Non-environmental score if job started now = 20.34 score (0-100, lower=better)
   Non-environmental score at optimal time    = 18.74 score (0-100, lower=better)
   Price if job started now                   = 26.91 EUR/MWh
   Price at chosen start time                 = 159.68 EUR/MWh (+ 132.78)

``carbon`` and ``water_stress`` show no price block at all, even though
DE generally has price coverage. Their optimal window falls outside the
horizon ``energy-charts.info`` currently has published (the ``carbon``
window lands on 2026-10-02, well ahead), so the report is omitted
entirely rather than showing half a comparison. ``water`` and
``environmental_score``, with closer optimal times, do fall inside that
window.

``environmental_score`` is wattnet's own composite score, already built
internally from the carbon, water and water stress dimensions. Treat it
as an alternative to combining ``carbon``/``water``/``water_stress``
yourself, not as an addition to them; see :ref:`cookbook-composite`
below for why blending them together double-counts.

.. _cookbook-composite:

Composite
---------

A single provider that detects whether the location is a UK postcode or
a wattnet.eu zone, and for each requested signal uses the native source
for that kind of location.

.. code-block:: console
   :caption: *Default combination for a UK postcode: the three
              no-authentication signals.*

   $ cats --duration 60 --location OX1 --api composite
   ...

   Composite score (carbon=0.33, price=0.33, renewables=0.33) if job started now = 0.04 0-1, lower=better
   Composite score (carbon=0.33, price=0.33, renewables=0.33) at optimal time    = 0.04 0-1, lower=better

``environmental_score`` is wattnet's own composite score and already
factors in the carbon, water and water stress dimensions internally.
Plain ``--api composite`` with no ``--signal`` blends *all* available
signals equally for a wattnet.eu zone, including ``carbon``/``water``/
``water_stress`` alongside ``environmental_score``, which double-counts
those dimensions. Pick ``environmental_score`` as a stand-in for all
three instead, and combine it only with signals it doesn't already
cover (``price``, ``renewables``):

.. code-block:: console
   :caption: *A clean blend for a wattnet.eu zone, avoiding double-counting.*

   $ cats --duration 60 --location DE --api composite --signal environmental_score=0.34 --signal price=0.33 --signal renewables=0.33
   ...

   Best job start time                                                                                                     = 2026-09-30 14:15:20
   Composite score (environmental_score=0.34, price=0.33, renewables=0.33) if job started now = 0.15 0-1, lower=better
   Composite score (environmental_score=0.34, price=0.33, renewables=0.33) at optimal time    = 0.15 0-1, lower=better
   Price if job started now                                                                                                = 107.33 EUR/MWh
   Price at chosen start time                                                                                              = 107.33 EUR/MWh (- 0.00)

.. code-block:: console
   :caption: *Cross-portal fallback, with a warning: environmental_score
              combined with price for a UK postcode.*

   $ cats --duration 60 --location OX1 --api composite --signal environmental_score=0.5 --signal price=0.5
   WARNING: 'OX1' has no environmental_score data source; using wattnet.eu's 'GB' zone instead (needs wattnet.eu credentials).
   ...

   Composite score (environmental_score=0.50, price=0.50) if job started now = 0.04 0-1, lower=better
   Composite score (environmental_score=0.50, price=0.50) at optimal time    = 0.04 0-1, lower=better

``environmental_score`` only exists on wattnet.eu, which has no postcode
granularity for GB; it falls back to the fixed ``GB`` zone. ``price``
still comes from ``octopus.energy`` for the real postcode.

XK (Kosovo) has no ``energy-charts.info`` price or renewables
equivalent, so only wattnet-backed signals exist there at all: ``carbon``,
``water``, ``water_stress`` and ``environmental_score``. Since
``environmental_score`` already covers all three of the others, there is
no non-redundant combination left to blend it with for this zone; the
only methodologically clean choice is ``environmental_score`` on its own:

.. code-block:: console
   :caption: *A zone with only partial signal support (XK): environmental_score alone.*

   $ cats --duration 60 --location XK --api composite --signal environmental_score=1.0
   ...

   Composite score (environmental_score=1.00) if job started now = 0.90 0-1, lower=better
   Composite score (environmental_score=1.00) at optimal time    = 0.03 0-1, lower=better

.. code-block:: console
   :caption: *Two kinds of error: an unknown signal name, and a real
              signal with no source for this location.*

   $ cats --duration 60 --location OX1 --api composite --signal not_a_signal=1.0
   Value error: Unknown signal(s) ['not_a_signal'] for the composite provider; valid signal names: ['carbon', 'environmental_score', 'price', 'renewables', 'water', 'water_stress']

   $ cats --duration 60 --location XK --api composite --signal price=1.0
   Invalid location: Signal(s) ['price'] have no data source for location 'XK' (wattnet_zone); available here: ['carbon', 'environmental_score', 'water', 'water_stress']

An unknown signal name always errors. A real signal with no source for
*this* location errors only if explicitly requested via ``--signal``;
otherwise it is silently excluded from the default blend.

.. _cookbook-price-constraint:

Price as a constraint, not a blended weight
--------------------------------------------

Optimising purely for carbon can land on a window that is more
expensive than right now: carbon and price are not perfectly
correlated. Instead of blending price into the score with
``--signal price=X`` (where it can end up dominating the decision),
``--max-price`` / ``--max-price-increase-pct`` treat it as a cap: the
chosen metric is still what is optimised, but only among the windows
that satisfy the cap.

.. code-block:: console
   :caption: *Unconstrained: the carbon optimum comes out pricier.*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk
   ...

   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 63.71 gCO2eq/kWh
   Price if job started now            = 153.39 GBP/MWh
   Price at chosen start time          = 219.20 GBP/MWh (+ 65.81)

.. code-block:: console
   :caption: *--max-price-increase-pct 0: never pay more than now.*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk --max-price-increase-pct 0
   ...

   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 66.10 gCO2eq/kWh
   Price if job started now            = 153.39 GBP/MWh
   Price at chosen start time          = 153.39 GBP/MWh (- 0.00)

The cap excludes the 219 GBP/MWh window, so it stays at "now", giving
up the carbon improvement to avoid paying more.

.. code-block:: console
   :caption: *A cap that does not bind, versus one that does.*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk --max-price 300
   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 63.71 gCO2eq/kWh
   Price at chosen start time          = 219.22 GBP/MWh (+ 65.83)

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk --max-price 160
   Carbon intensity if job started now = 66.10 gCO2eq/kWh
   Carbon intensity at optimal time    = 66.10 gCO2eq/kWh
   Price at chosen start time          = 153.40 GBP/MWh (- 0.00)

300 is higher than the ~219 the real optimum would cost, so it excludes
nothing; the result is identical to the unconstrained run. 160 is below
it, so it excludes that window and the schedule stays at "now". The cap
only changes anything once it is tighter than the price the
unconstrained optimum would actually cost.

.. code-block:: console
   :caption: *Failure modes: an impossible cap, and a location with no
              price coverage at all.*

   $ cats --duration 60 --location OX1 --api carbonintensity.org.uk --max-price 1
   Price constraint not satisfiable: No candidate start time both falls within price data's forecast horizon and satisfies the price constraint (cap=1.00); try relaxing --max-price/--max-price-increase-pct or removing it.

   $ cats --duration 60 --location XK --api wattnet.eu --max-price 100
   Invalid location: XK. No day-ahead price data available for this location; cannot use --max-price/--max-price-increase-pct here.

No silent fallback: if nothing satisfies the cap, or the location has
no price signal at all, CATS raises a clear error rather than
scheduling against an unverified constraint. ``--max-price`` and
``--max-price-increase-pct`` are mutually exclusive (an ``argparse``
error if both are given).

Flag cheat sheet
-----------------

======================================  ===============================================================
Flag                                    What it does
======================================  ===============================================================
``--metric NAME``                       Which metric to request from the chosen provider (if it
                                         supports more than one)
``--signal NAME=WEIGHT``                Repeatable. Signal and weight to blend in ``composite``
``--max-price N``                       Absolute price cap, in the location's native unit
``--max-price-increase-pct N``          Price cap relative to the price right now
``--list-providers``                    List providers, metrics and capabilities, without needing
                                         ``--duration``
``--list-locations``                    List the valid ``--location`` codes of one provider (or all),
                                         without needing ``--duration``
======================================  ===============================================================

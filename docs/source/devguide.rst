.. _devguide:

Developer's guide
=================

We have split the documentation and information about contributing to CATS into three pages. On this
page you will find information mostly focussing on how to contribute code to CATS. We also have a guide to
:ref:`contributing` ideas, questions and bug reports as well as a :ref:`maintenanceguide` which focusses on
tips and tools for maintainers (e.g. creating a new release).

I Want To Contribute
--------------------

We are looking for contributions that improve the functionality of CATS, help enhance the community of developers and users
of CATS, and allow the long-term stability of the CATS project. We have developed the guidance below with these aims in
mind.

.. NOTE::
  When contributing to this project, you must agree that you have authored 100% of the content, that you have the
  necessary rights to the content and that the content you contribute may be provided under the project license.
  All contributors are expected to abide by our code of conduct (see
  `CODE_OF_CONDUCT.md <https://github.com/GreenScheduler/cats/blob/main/CODE_OF_CONDUCT.md>`__ in the repository)
  and to disclose the use of AI tools.

Adding a feature / making a change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All significant changes should be discussed in an issue (as outlined in :ref:`contributing`) before
time is spent writing code,
and we would like changes to be fed into the CATS code via a pull
request against the ``main`` branch on github. These pull requests should
outline the reason for the change,
reference any previous discussion, and note any significant issues that may need
further consideration. A maintainer with write access to the main
CATS repository who has not been directly involved in
writing the new code or documentation will need to review the pull request
(see :ref:`maintenanceguide`) prior to merging.

Pull requests should also:

1. Include confirmation that the named author(s) are able to assert copyright, legal, and moral ownership
   on their contribution. Because contributors to CATS do not assign copyright this important to protect the
   ongoing development of the software.
2. Agree to release their contribution under the
   `MIT license <https://github.com/GreenScheduler/cats/blob/main/LICENSE>`__.
3. Are willing and able to discuss their proposed contribution in a constructive way
   with reviewers.
4. Disclosure of any use of AI tools as described in the AI use policy below.

We have set up pull request templates to remind contributors to check these items.

Code style, tests and documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We do not have a formal style guide, but code changes and additions should seek to follow the style
established by the existing CATS codebase. We have a precommit git hook that can be used to run
Ruff to help maintain a consistent style. CATS has a fairly comprehensive test suite that runs
automatically against all pull requests and new code should either come with new tests or with an
explanation about why tests for the new code are not included. Please indicate where changes to
behavior have been made (especially where this means changes to the tests have also been needed).
CATS includes documentation which should be updated by the pull requests making changes to the
code (although documentation only pull requests are welcome). Some of this documentation is
automatically generated (from doc strings and help text for command line tools) so please make
sure that this internal documentation is up to date.

We use `pre-commit <https://pre-commit.com>` to automatically check linting and perform auto-formatting.
You can install pre-commit using your package manager and install the git hooks (only needs to be performed once):

  pre-commit install

Once the hook is installed, pre-commit will automatically check each commit.

Running Tests
^^^^^^^^^^^^^

Testing can also be undertaken in an isolated environment prior to making a pull request and this
can make code development significantly easer. We run tests using ``flake8`` for basic linting,
``pytest`` for the majority of unit and integration tests, and ``mypy`` to check type annotations
and for the static analysis this permits. In a checked out copy of the source, the following installs
the prerequisites and runs all tests::

  python3 -m pip install '.[test]'
  python3 -m pip install flake8
  python3 -m pip install '.[types]'
  flake8 . --count --select=E9,F63,F7,F82 --show-source
  python3 -m mypy cats
  python3 -m pytest

A new build incorporating any updates to the documentation is automatically generated for each PR
and will become available from a link within the pull request.

Building documentation
^^^^^^^^^^^^^^^^^^^^^^

Documentation is built and updated automatically when pull requests are created and merged. However,
it is sometimes useful to build documentation locally. This can be done by running the following in
a checked out copy of the source::

  python3 -m pip install '.[docs]'
  cd docs
  make html

Updated HTML documentation can then be found in the ``docs/build/html`` directory.

AI policy
^^^^^^^^^

It is important to us that contributions help enhance the community of developers and users
of CATS, and allow the long-term stability of the project. With this in mind we have chosen not
to forbid contributions created with the support of AI tools but instead have created the following
policy. The CATS maintainers reserve the right to alter this policy without notice and to summarily
reject contributions and block contributors who they suspect of violating this policy.

1. Whether developed with the assistance of AI tools or not, all contributors must be in a position to
   assert moral ownership and copyright on their own contributions such that they can grant a license
   for use, distribution and modification. We note that contributors to CATS
   retain the copyright on their own contribution (granting a license for use and modification as described
   in the LICENSE file) and that the legal and moral ownership of content
   created by AI tools is a complex and unresolved
   area of law and ethics. Contributors are expected to carry the risk of any choice to use AI tools. This
   means that contributions from accounts that themselves appear to be generated by AI tools are unlikely to
   be accepted.
2. Whether developed with the assistance of AI tools or not, all contributors must be in a position to
   discuss and explain their own proposed contributions. This is to allow us to assess the contribution
   for long-term sustainability in a way that does not put too great a burden on the maintenance team.
   This means that contributions that are created entirely by AI agents without (or with very limited)
   human interaction are unlikely to be accepted.
3. Contributors must disclose the use of AI tools alongside any submission. This should be done within the
   pull request and should include details of what tool(s) have been used, how the tool(s) were used, and
   how the resulting code has been checked and validated.
4. We expect all contributors to enter into discussion as a person. AI agents should not be permitted to
   open or contribute to pull requests or issues.

In any case, we will always assess the future maintainability of proposed changes alongside other objectives
of the project. In particular, we ask that contributors are mindful of the climate impact of creating CATS
so only use AI tools where this is appropriate (so, for trivial tasks please use other, less energy intensive
tools) and of the need to allow an on-ramp for new contributors (so don't use an AI tool to address issues that
are marked "good first issue" that can be used to as a way for contributors to become familiar with the codebase).

Contributor how-to guide
------------------------

There are several tasks and areas of the code that may be of particular interest to multiple
contributors. Some guidance on these is provided below.

Adding a data provider
^^^^^^^^^^^^^^^^^^^^^^

CATS is designed to take forecasts of the future carbon intensity of the electricity supply from different
sources. Within the code, each of these forecast sources is represented by a "provider" which is an
implementation of the ``cats.providers.BaseProvider`` abstract base class. These implementations are
responsible for downloading data from a remote forecast source, formatting that data such that it can
be used by CATS and providing some basic information to CATS about the properties of the forecast. Typically,
forecasts are local to a particular area and the provider is responsible for validating any location information
provided. The provider is also responsible for managing any authentication. Tools are provided to ensure that HTTP requests
are cached and have the CATS HTTP header included. In order to optimize this caching providers should also suitably
align the time of requests for forecast data such that repeated requests in a short time period are served from
the local cache rather than as a series of slightly different hits on the remote server.

The best way to add a new provider is to use ``cats/providers/gb_carbonintensity.py`` (which does not
involve authentication) or ``cats/providers/eu_wattnet.py`` (which does) as a starting point and modify
for your needs. Important things to consider are the structure of any returned JSON objects, the duration
of the forecast and the frequency of data points, issues around authentication and data validation, and the
best way to encode and validate location information. Much of the work belongs in the ``get_data()`` method
which typically builds a request URL (including suitably aligned time and location information), uses the ``fetch_url()`` function
from ``cats/providers/base.py`` to download the data and convert JSON to python objects, and then places this
data in ``Timeseries`` of ``PointEstimate`` objects, which are returned.

Providers should also override ``list_locations()``, returning one ``LocationGroup`` per location encoding
(more than one when the codes depend on the metric), so that users can discover valid codes with
``--list-locations``. Each code listed must be accepted by ``validate_location()``.

New providers should be listed in ``cats/providers/__init__.py`` and registered using the ``@provider`` decorator
(the argument of this decorator is used to allow the user to select the provider). Tests should be included.

``cats/providers/eu_energycharts.py`` and ``cats/providers/gb_octopus.py`` are further no-auth examples,
returning a different metric (day-ahead electricity price rather than carbon intensity) instead of a
different region. Two gotchas found while writing them, worth checking for any new provider:

- The ``PointEstimate`` list returned by ``get_data()`` must be sorted in ascending order by ``datetime``;
  not every upstream API returns data in chronological order (Octopus Energy's API returns most-recent-first).
- When aligning the request timestamp down to the provider's native resolution for cache-friendliness, round
  down to the exact boundary of the current interval rather than a minute or so into it. Some APIs filter on
  "interval start >= requested start", so requesting a time a minute after the boundary can exclude the
  currently in-progress interval and leave a gap between "now" and the first returned data point. Use
  ``align_to_resolution()`` from ``cats/providers/base.py`` for this rather than writing the rounding
  arithmetic again: it is shared by every bundled provider, so a fix to it fixes this class of bug everywhere
  at once, rather than needing to be independently rediscovered and patched per provider.

A single provider can serve more than one metric from the same API portal, selected by the caller via the
``metric`` parameter threaded through ``get_data()``, ``get_max_duration_minutes()`` and
``get_temporal_resolution_minutes()`` (exposed on the CLI as ``--metric``). A provider opts into this by
declaring ``SUPPORTED_METRICS`` (a ``frozenset`` of valid metric names) and ``DEFAULT_METRIC`` as class
attributes, then calling ``resolve_metric(metric, self.SUPPORTED_METRICS, self.DEFAULT_METRIC)`` at the
start of each of those three methods; this validates the requested metric (raising ``InvalidMetricError``
for an unknown one) and falls back to the default when the caller passes ``None``. A provider that only
ever serves one implicit metric can leave ``SUPPORTED_METRICS`` at its empty default and ignore the
``metric`` parameter entirely.

``cats/providers/gb_carbonintensity.py`` (``carbon``, ``renewables``) and ``cats/providers/eu_wattnet.py``
(``carbon``, ``water``, ``water_stress``, ``environmental_score``) are worked examples. The
carbonintensity.org.uk case is the simplest: both metrics come from a single API call (the response
already includes both "intensity" and "generationmix" for every period), so ``get_data()`` makes the same
request regardless of ``metric`` and only changes which field it extracts; requesting both metrics in the
same run (e.g. via the ``composite`` provider) costs only one real HTTP request, the second being served
from the shared ``fetch_url()`` cache. wattnet.eu is the more general case: each metric maps to a genuinely
different endpoint (not just a different query parameter on one endpoint), so the provider keeps a small
``metric -> (path, query_params)`` table and dispatches the URL build and the parsed ``Timeseries.metric``
name from it, while still sharing one parsing routine since all three endpoints return the same
series/values response shape. Two further things worth checking for any new multi-metric provider:

- Don't assume every value an API's own parameter-validation error message lists as "accepted" actually
  has real data behind it - the Energy-Charts ``/v2/signal`` endpoint (used for ``energy-charts.info``'s
  ``renewables`` metric) accepts several country codes (``uk``, ``ba``, ``cy``, ``ge``, ``ie``, ``md``,
  ``rs``, ``ua``, ``xk``) that return an empty ``data: []``. Confirm live data point counts per value you
  plan to support, not just which values the API's own validation lets through.
- If different metrics on the same provider need different location encodings (``energy-charts.info``'s
  ``price`` needs a bidding zone like ``DE-LU``, its ``renewables`` needs a plain country code like
  ``de``), ``validate_location()`` itself has no ``metric`` parameter to disambiguate against, so it can
  only apply a best-effort check (e.g. accept whichever scheme matches). Do the metric-specific, strict
  check inside ``get_data()`` instead, once ``metric`` is known there.
- If a metric's own polarity is undocumented by the upstream API (e.g. no stated "higher/lower is
  better"), confirm it rather than guessing, and document the confirmed polarity explicitly in both
  the docstring and a comment at the point of inversion.

A provider does not have to call an external API directly at all. ``cats/providers/composite.py`` instead
wraps a *registry* of named signals (``carbon``, ``price``, ``renewables``, ``water``,
``water_stress``, ``environmental_score``), built per request from a ``(provider instance, metric,
location, optional note)`` tuple per signal - the same provider instance can back two different signals on
two different metrics, as ``carbon`` and ``renewables`` both do on ``GBCarbonIntensityProvider`` for a GB
postcode. Unlike a single-portal multi-metric provider, ``composite``'s location can be either of two
different kinds (a GB postcode outward code or a wattnet.eu zone code); ``_detect_location()`` tries the GB
postcode scheme first, falling back to the wattnet.eu zone scheme, so a code valid under both (``SE1``-
``SE4``, which collide between South East London postcodes and Swedish wattnet.eu price zones) is always
interpreted as the GB postcode. ``_signal_specs()`` then builds the registry appropriate to that location
kind: for a GB postcode, the three wattnet-only signals fall back to wattnet.eu's fixed ``GB`` zone (with a
note logged via ``logging.warning()`` at the point they're used, since this substitutes a country-wide
value for what looks like a postcode-specific request); for a wattnet.eu zone, ``price`` and ``renewables``
are only included when a static lookup table (for price) or a derivation rule with explicit exceptions
(for renewables) actually has an ``energy-charts.info`` equivalent for that zone, since the two portals'
zone/country naming schemes differ and neither response exposes the other's encoding directly. Prefer
deriving a location translation live where possible (as the GB postcode's Octopus region letter is,
from a field already present in carbonintensity.org.uk's own API response), and fall back to an explicit,
documented table or rule (including *why* any zones are left unmapped) rather than guessing.

The normalise-and-combine logic (independently min-max normalising each selected signal over the fetched
window, then a configurable weighted sum) lives alongside it as a handful of pure functions
(``normalise()``, ``resolve_weights()``, ``combine_series()``) at the top of ``composite.py``, kept free of
any location/routing concerns so they stay easy to reason about in isolation. This is a useful pattern for
combining metrics without touching the scheduling algorithm itself, and generalises
beyond a fixed set: the CLI's repeatable ``--signal NAME=WEIGHT`` lets the user pick any subset of the
signals available for their location. When a signal isn't available for a given location at all, fail
loudly (``InvalidLocationError``) if the user explicitly asked for that signal via ``--signal``, but
silently exclude it from the default (unrequested) combination rather than breaking locations that never
had it; separately, an entirely unrecognised signal *name* (not a valid signal at all, regardless of
location) should always fail loudly with ``ValueError`` when explicitly requested via ``--signal``.

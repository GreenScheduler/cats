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

The best way to add a new provider is to use ``cats/providers/uk_carbonintensity.py`` (which does not
involve authentication) or ``cats/providers/eu_wattnet.py`` (which does) as a starting point and modify
for your needs. Important things to consider are the structure of any returned JSON objects, the duration
of the forecast and the frequency of data points, issues around authentication and data validation, and the 
best way to encode and validate location information. Much of the work belongs in the ``get_data()`` method
which typically builds a request URL (including suitably aligned time and location information), uses the ``fetch_url()`` function
from ``cats/providers/base.py`` to download the data and convert JSON to python objects, and then places this
data in ``Timeseries`` of ``PointEstimate`` objects, which are returned.

New providers should be listed in ``cats/providers/__init__.py`` and registered using the ``@provider`` decorator
(the argument of this decorator is used to allow the user to select the provider). Tests should be included. 
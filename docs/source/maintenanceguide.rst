.. _maintenanceguide:

Maintainer's guide
==================

We have split the documentation and information about contributing to CATS into three pages. On this
page you will find information mostly focussing on how we maintain CATS. We also have a guide to
:ref:`contributing` ideas, questions and bug reports as well as a :ref:`devguide` which focusses on
contributing code.

.. NOTE::
  Maintainers are expected to set a example to the community by following the guidance in :ref:`contributing`
  and :ref:`devguide` as well as following the
  `CODE_OF_CONDUCT.md <https://github.com/GreenScheduler/cats/blob/main/CODE_OF_CONDUCT.md>`__ in the repository
  and our policy around the use of AI tools.

The CATS maintainers are those of us who have direct commit access to the CATS github repository. Maintainers can
choose (without explanation) to relinquish this responsibility while remaining a part of the CATS developer community
and new maintainers can be added following a consensus amongst the existing maintainers. If needed, a majority of maintainers
can act together to remove a maintainer.

Maintainers will, by agreement amongst themselves, ensure that a subset of maintainers are appointed to act as points
of contact for code of conduct and security reports. They will also ensure that sufficient maintainers have access to the
other tooling used to maintain, develop and distribute CATS (such as PyPI and ReadTheDocs). Maintainers must individually
ensure that their authentication tokens are secure for all these services using multi-factor authentication where available.

Maintainers are collectively responsible for reviewing contributions before they are incorporated into CATS. At a minimum there
should be a review by one maintainer who was not involved in making the change and this should incorporate a checks that the
idea behind the change will improve CATS, that the long-term maintainability of the code is not unnecessarily compromised,
that the change is tested and the new and old tests pass, that the change is documented, and that the developer has followed our
policies. Once a maintainer has confirmed that they are content by completing their review code can be merged by them or by any other
maintainer (including by a maintainer who has created the change). It will often be the case that some revision of the proposed
changes will be required.

Developer how-to guide
------------------------

There are several tasks that must be repeatedly undertaken by maintainers. Some guidance on these is provided below.

Making a new release
^^^^^^^^^^^^^^^^^^^^

Those of us with commit access to the main CATS repository on GitHub are able to generate a new release and publish this to PyPI. This
should be discussed ahead of time (via a PR changing the version string, see 1 below) and once broad agreement is in place a release can be created as follows:

 1. Merge a pull request onto main that updates the CATS version number ``version`` in ``version.py`` and adds any release notes / key changes to the documentation. We use a "major.minor.patch" semantic versioning scheme; for bug fixes etc. bump the patch number, for significant new features bump the minor version number, for changes that break previous behavior update the major version number.
 2. Check that all tests have passed after the merge and that the "latest" documentation at read the docs is updated.
 3. Create a release via the GitHub web interface. This involves creating a new tag ("v1.2.3" for version "1.2.3"), giving the release a name (just "1.2.3"), and adding short release notes using markdown as needed. Make sure this is "set as the latest release".
 4. After a short time you should be able to check that the new release exists on PyPI and is documented in the stable docs on read the docs.

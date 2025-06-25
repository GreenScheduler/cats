.. _contributing:

.. _GitHubrepo: https://github.com/GreenScheduler/cats

Contributing
============

First off, thanks for taking the time to contribute!

All types of contributions are encouraged and valued. See the below for different ways to help and details about how this project handles them. Please make sure to read the relevant section before making your contribution. It will make it a lot easier for us maintainers and smooth out the experience for all involved. The community looks forward to your contributions. All contributors are expected to abide by our code of conduct (see CODE_OF_CONDUCT.md in the repository). 

.. NOTE::
  And if you like the project, but just don't have time to contribute, that's fine. There are other easy ways to support the project and show your appreciation, which we would also be very happy about.
  These include staring the project, writing about the project, referring to this project in your project's readme,
  mentioning the project at local meetups, and telling your friends/colleagues.


I Have a Question
-----------------

.. NOTE::
  If you want to ask a question, we assume that you have read the available documentation (at https://cats.readthedocs.io/).

Before you ask a question, it is best to search for existing issues (see https://github.com/GreenScheduler/cats/issues) that might help you. In case you have found a suitable issue and still need clarification, you can write your question in this issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

* Open an issue (https://github.com/GreenScheduler/cats/issues/new).
* Provide as much context as you can about what you're running into.
* Provide project and platform versions (python version etc), depending on what seems relevant.
* We use labels on GitHub to manage issues. Please add the "question" label to your issue.

We will then take care of the issue as soon as possible. 


I Want To Contribute
--------------------

.. NOTE::
  When contributing to this project, you must agree that you have authored 100% of the content, that you have the necessary rights to the content and that the content you contribute may be provided under the project licence.

Reporting Bugs
--------------

Before Submitting a Bug Report
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A good bug report shouldn't leave others needing to chase you up for more information. Therefore, we ask you to investigate carefully, collect information and describe the issue in detail in your report. Please complete the following steps in advance to help us fix any potential bug as easily as possible.

* Make sure that you are using the latest version.
* Determine if your bug is really a bug and not an error on your side e.g. using incompatible environment components/versions. Make sure that you have read the documentation at https://cats.readthedocs.io/). If you are looking for support, you might want to check the section above.
* To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the bug tracker (see https://github.com/GreenScheduler/cats/issues?q=label%3Abug).
* Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
* Collect information about the bug:

  * OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
  * Version of python and your python environment, package manager, and how you installed CATS.
  * Possibly your input and the output
  * Can you reliably reproduce the issue? And can you also reproduce it with older versions?


How Do I Submit a Good Bug Report?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. NOTE::
  You must never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Instead sensitive bugs must be sent by email to Andrew Walker (andrew.walker@earth.ox.ac.uk) and/or
  Loïc Lannelongue (ll582@medschl.cam.ac.uk) .

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

* Open an Issue at https://github.com/GreenScheduler/cats/issues/new. (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
* Explain the behavior you would expect and the actual behavior.
* Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
* Provide the information you collected in the previous section.

Once it's filed:

* The project team will label the issue accordingly.
* A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
* If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).


Suggesting Enhancements
-----------------------

This section guides you through submitting an enhancement suggestion for cats, **including completely new features and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community to understand your suggestion and find related suggestions.

Before Submitting an Enhancement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Make sure that you are using the latest version.
* Read the documentation at https://cats.readthedocs.io/ carefully and find out if the functionality is already covered, maybe by an individual configuration.
* Search https://github.com/GreenScheduler/cats/issues to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.
* Find out whether your idea fits with the scope and aims of the project. It's up to you to make a strong case to convince the project's developers of the merits of this feature. Keep in mind that we want features that will be useful to the majority of our users and not just a small subset. If you're just targeting a minority of users, consider writing an add-on/plugin library.

How Do I Submit a Good Enhancement Suggestion?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enhancement suggestions are tracked as GitHub issues (https://github.com/GreenScheduler/cats/issues).

* Use a **clear and descriptive title** for the issue to identify the suggestion.
* Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point you can also tell which alternatives do not work for you.
* **Explain why this enhancement would be useful** to most cats users. You may also want to point out the other projects that solved it better and which could serve as inspiration.

Contributing code or documentation
----------------------------------

We also welcome contributions in the form of improvements to the code or documentation. Information to help make this process as smooth as possible is below.

Adding a feature / making a change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ideally, all significant changes would be discussed in an issue as outlined above before 
time is spent writing code (see asking questions, reporting bugs, and suggesting enhancements),
but however changes are made we would like them to be fed into the CATS code via a pull 
request against the ``main`` branch on github. These pull requests should 
outline the reason for the change,
reference any previous discussion, and note any significant issues that may need 
further consideration. A maintainer with write access to the main 
CATS repository who has not been directly involved in
writing the new code or documentation will need to review the pull request prior to merging. 

We do not have a formal style guide, but code changes and additions should seek to follow the style 
established by the existing CATS codebase. CATS has a fairly comprehensive test suite that runs
automatically against all pull requests and new code should either come with new tests or with an
explanation about why tests for the new code are not included. Please indicate where changes to 
behavior have been made (especially where this means changes to the tests have also been needed).  
CATS includes documentation which should be updated by the pull requests making changes to the
code (although documentation only pull requests are welcome). Some of this documentation is
automatically generated (from doc strings and help text for command line tools) so please make
sure that this internal documentation is up to date.

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

Updated documentation is automatically generated for PRs and will be available from a link within
the pull request. 

Making a new release
^^^^^^^^^^^^^^^^^^^^

Those of us with commit access to the main CATS repository on GitHub are able to generate a new release and publish this to PyPi. This
should be discussed ahead of time (via a PR changing the version string, see 1 below) and once broad agreement is in place a release can be created as follows:

 1. Merge a pull request onto main that updates the CATS version number ``__version__`` in ``__init__.py`` and adds any release notes / key changes to the documentation. We use a "major.minor.patch" semantic versioning scheme; for bug fixes etc. bump the patch number, for significant new features bump the minor version number, for changes that break previous behavior update the major version number.
 2. Check that all tests have passed after the merge and that the "latest" documentation at read the docs is updated.
 3. Create a release via the GitHub web interface. This involves creating a new tag ("v1.2.3" for version "1.2.3"), giving the release a name (just "1.2.3"), and adding short release notes using markdown as needed. Make sure this is "set as the latest release".
 4. After a short time you should be able to check that the new release exists on PyPI and is documented in the stable docs on read the docs.   

Attribution
-----------

This guide is based on https://contributing.md/generator


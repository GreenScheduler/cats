.. _introduction:

.. The list below references links that may be used in more than one place
.. _SSIsite: https://www.software.ac.uk/
.. _CW23page: https://software.ac.uk/cw23
.. _CW23HackDaypage: https://www.software.ac.uk/cw23/hack-day
.. _NationalGridESO: https://www.nationalgrideso.com/
.. _CarbonIntensityAPI: https://carbonintensity.org.uk/
.. _GitHubrepoissues: https://github.com/GreenScheduler/cats/issues


Introduction
============

CATS is a **C**\limate-**A**\ware **T**\ask **S**\cheduler. It schedules
cluster jobs to minimize predicted carbon intensity of running the process.


Summary
-------

The Climate-Aware Task Scheduler is a lightweight Python package designed
to schedule tasks based on the estimated carbon intensity of the
electricity grid at any given moment.

This tool uses real-time
carbon intensity data from the `National Grid ESO <NationalGridESO_>`_
via `their API <CarbonIntensityAPI_>`_ to
estimate the carbon intensity of the electricity grid, and schedules
tasks at times when the estimated carbon intensity is lowest. This
helps to reduce the carbon emissions associated with running
computationally intensive tasks, making it an ideal solution for
environmentally-conscious developers.


Scope
-----

Currently CATS only works in the UK. If you are aware of APIs for
realtime grid carbon intensity data in other countries, please
`open an issue <GitHubrepoissues_>`_ to let us know.


Background
----------

It was created as part of the
`Software Sustainability Institute’s <SSIsite_>`_
`Collaborations Workshop 2023 <CW23page_>`_
`Hack Day <CW23HackDaypage_>`_.


Features
--------

* Estimates the carbon intensity of the electricity grid in real-time
* Schedules tasks based on the estimated carbon intensity, minimizing
  carbon emissions
* Provides a simple and intuitive API for developers
* Lightweight and easy to integrate into existing workflows
* Supports Python 3.9+

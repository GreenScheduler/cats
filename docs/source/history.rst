.. _history:

.. References to links that may be used in more than one place
.. _SSIsite: https://www.software.ac.uk/
.. _CW23page: https://software.ac.uk/cw23
.. _CW23HackDaypage: https://www.software.ac.uk/cw23/hack-day
.. _TuringWayChapter: https://book.the-turing-way.org/ethical-research/activism/activism-env-impact/#er-activism-env-impact-schedule-low-emission
.. _CarbonIntensityAPI: https://carbonintensity.org.uk/

History
=======

The initial version of CATS was created as part of the
`Software Sustainability Institute’s <SSIsite_>`_
`Collaborations Workshop 2023 <CW23page_>`_
`Hack Day <CW23HackDaypage_>`_ in Manchester where a team of ten of us (Colin Sauzé,
Sadie Bartholomew, Andrew Walker, Loïc Lannelongue, 
Thibault Lestang, Tony Greenberg, Lincoln Colling, 
Adam Ward, Abhishek Dasgupta and Carlos Martinez) spent an
intense day working to build a carbon-aware scheduler
(CATS) and to write a first draft of a chapter for inclusion in *The Turing Way*
on `the environmental impact of digital research <TuringWayChapter_>`_.
By the end of that day we had a working prototype of CATS that could
schedule tasks on the command line using the `at` command and data
from the `Carbon intensity API <CarbonIntensityAPI_>`_ 

During 2024 the `Software Sustainability Institute <SSIsite_>`_ provided funding
to allow some of us to dedicate further time to the development of CATS. This
led to the ability to schedule in user space using a SLURM scheduler, significant
clean-up of the code, the creation of a robust test suite, an update to the
documentation, publishing of version 1.0 on PyPI and of a paper in the Journal 
of Open Source Software (`doi:10.21105/joss.08251 <https://doi.org/10.21105/joss.08251>`_).
In addition, this work involved an investigation of how similar time-shifting approaches
could be applied to shared computing facilities and the creation of modules implementing the
same basic approach as that taken by CATS in a form that can be directly plugged into 
the SLURM scheduler.

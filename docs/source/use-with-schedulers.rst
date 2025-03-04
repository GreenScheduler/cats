.. _use-with-schedulers:

Use with Schedulers
===================

Using CATS with the ``at`` scheduler
------------------------------------

You can use CATS with the ``at`` job scheduler by running:

.. code-block:: console

   $ cats -d <job_duration> --loc <postcode> --scheduler at --command '<command>'

As an example, if you want to schedule a run of ``ls`` with a 5 minute
duration, in the 'OX1' postcode that would look like:

.. code-block:: console

   $ cats -d 5 --loc OX1 --scheduler at --command 'ls'

Using CATS with the ``sbatch`` scheduler
----------------------------------------

CATS provides a wrapper around ``sbatch`` to enable deferring job execution
till the optimal start time:

.. code-block:: console

   $ cats -d <job_duration> --loc <postcode> --scheduler sbatch --command ./script.sh


Demonstration
^^^^^^^^^^^^^

.. image:: ../../cats.gif
  :width: 400
  :alt: A video demonstration of CATS being used standalone and with ``at``.
  :align: center

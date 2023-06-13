.. _use-with-schedulers:

Use with Schedulers
===================

Using CATS with the ``at`` scheduler
------------------------------------

You can use cats with the ``at`` job scheduler by running:

.. code-block:: console

   $ <command> | at -t `python -m cats -d <job_duration> --loc <postcode>`

As an example, if you want to schedule a run of ``ls`` with a 5 minute
duration, in the 'OX1' postcode that would look like:

.. code-block:: console

   $ ls | at -t `python -m cats -d 5 --loc OX1`


Demonstration
^^^^^^^^^^^^^

.. image:: ../../cats.gif
  :width: 400
  :alt: A video demonstration of CATs being used standalone and with ``at``.
  :align: center

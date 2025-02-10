.. _how-to:

How-to guides
*************

These guides accompany you through the complete COS stack operations lifecycle.


.. note::

   If you are looking for instructions on how to get started with COS Lite, see
   :ref:`the tutorial section <tutorial>`.

Migrating
=========

These guides till assist existing users of other observability stacks offered by
Canonical in migrating to COS Lite or the full COS.

.. toctree::
   :maxdepth: 1

   Migrate from LMA to COS <migrate-lma-to-cos-lite>
   Migrate from COS Lite to COS <migrate-cos-lite-to-cos>

Configuring
=============

Once COS has been deployed, the next natural step would be to integrate your charms and workloads
with COS to actually observe them.

.. toctree::
   :maxdepth: 1

   Exposing a metrics endpoint <exposing-a-metrics-endpoint>
   Integrating COS Lite with uncharmed applications <integrating-cos-lite-with-uncharmed-applications>
   Configure scrape jobs <configure-scrape-jobs>
   Disable charmed rules <disable-charmed-rules>

Troubleshooting
===============

During continuous operations, you might sometimes run into issues that you need to resolve. These
how-to guides will assist you in troubleshooting COS in an effective manner.   

.. toctree::
   :maxdepth: 1

   Troubleshooting `Gateway address unavailable` in Traefik <troubleshoot-gateway-address-unavailable>
   Troubleshooting `socket: too many open files` <troubleshoot-socket-too-many-open-files>
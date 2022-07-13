DataLad extension for working with Debian packages and package repositories
***************************************************************************

.. image:: _static/datalad_debian_logo_with_names.svg
   :width: 50%
   :align: center

This software wraps **building and disseminating Debian packages** in a
standard **data management task**. While there is no shortage of specialized
software solutions for Debian package workflows and archives, here, the general
purpose data management solution `DataLad <https://datalad.org>`__ is used to
present all involved steps as a system that tracks inputs, and converts them to
outputs, with **full capture of actionable provenance** information for all
respective transformations.  Importantly, the system is **fully decentralized**
and whole processes and/or individual steps can be performed by independent
collaborators with **no required access to a common build or distribution
infrastructure**.

Features include:

- Version control of Debian source packages, and/or provenance capture of
  generating such source packages from upstream sources
- Building Debian binary packages from source packages (reproducibly) in
  portable, containerized build environments
- Maintain collections of source and binary packages built for a given
  target distribution release, to provide or maintain access to
  historical build artifacts similar to https://snapshot.debian.org
- Generate and update APT package repositories for particular versions of
  a package collection

This software only implements the data management and provenance tracking
features. Specialized tasks, such as repository generation, or building
binary packages from source packages are performed using standard solutions
such as `reprepro <https://salsa.debian.org/brlink/reprepro>`__, or
`dpkg <https://www.dpkg.org>`__


Overview
========

.. toctree::
   :maxdepth: 1

   concepts
   usage



Commands and API
================

.. toctree::
   :maxdepth: 2

   cmdline
   modref


.. |---| unicode:: U+02014 .. em dash

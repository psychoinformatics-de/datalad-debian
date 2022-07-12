DataLad extension for working with Debian packages and package repositories
***************************************************************************



This software provides functionality to create DataLad-based structures for building and disseminating Debian packages.
Its major aims are threefold:

- It simplifies the Debian package build process by wrapping a build workflow into DataLad convenience commands
- With DataLad's provenance capture and version control features, it provides a basis for reproducibly building and updating packages
- It creates a readily serveable package archive

.. image:: _static/datalad_debian_logo_with_names.svg
   :width: 50%
   :align: center

Overview
========

.. toctree::
   :maxdepth: 1

   concepts



API
===
  
High-level API commands
-----------------------
  
.. currentmodule:: datalad.api
.. autosummary::
   :toctree: generated

   deb_new_distribution
   deb_configure_builder
   deb_bootstrap_builder
   deb_new_package
   deb_build_package
   deb_new_reprepro_repository
   deb_add_distribution


Command line reference
----------------------

.. toctree::
   :maxdepth: 1

   generated/man/datalad-deb-new-distribution
   generated/man/datalad-deb-configure-builder
   generated/man/datalad-deb-bootstrap-builder
   generated/man/datalad-deb-new-package
   generated/man/datalad-deb-build-package
   generated/man/datalad-deb-new-reprepro-repository
   generated/man/datalad-deb-add-distribution


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. |---| unicode:: U+02014 .. em dash

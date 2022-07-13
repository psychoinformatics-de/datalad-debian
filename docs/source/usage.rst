Quick Start
***********


Create a distribution dataset
=============================

To create a collection of packages for a particular distribution (e.g. Debian
11, bullseye), start by creating a ``distribution`` dataset.

.. code-block:: bash

   datalad deb-new-distribution bullseye
   cd bullseye

This creates the ``distribution`` dataset "bullseye" and a ``builder`` subdataset
that contains the subdirectories:

* ``envs``: generated build environments for any number of target CPU
  architectures

* ``recipes``: actionable descriptions for (re)creating a build
  environment (e.g. singularity recipe)

::

   bullseye
   └── builder
        ├── envs
        │   └── README.md
        └── recipes
            └── README.md

Configure and create a package builder
======================================

The ``builder`` subdataset can be configured to provide one or more
containerized environments for building packages for the respective distribution
and target CPU architecture. Start by configuring the builder for the specific
distribution release.

.. code-block:: bash

   datalad deb-configure-builder --dataset builder dockerbase=debian:bullseye

This creates a builder recipe for Debian bullseye based on a template for
dockerbase. The command ``deb-bootstrap-builder`` can now be run to bootstrap
the (containerized) build environment based on the recipe just created.

.. code-block:: bash

   datalad deb-bootstrap-builder --dataset builder

The ``builder`` dataset now contains a container image that can be used for
building packages. Finally, save the results of the build configuration and
creation in the ``distribution`` dataset.

.. code-block:: bash

   datalad save --dataset . --message "Update distribution builder" builder

::

   bullseye
   └── builder
        ├── envs
        │   ├── README.md
        │   └── singularity-amd64.sif
        └── recipes
            ├── README.md
            └── singularity-any


Add a package to the distribution
=================================

To add a package, start by creating a new ``package`` dataset inside of the
``distribution`` dataset.

.. code-block:: bash

   datalad deb-new-package hello

This creates a new ``package`` subdataset for the hello package under the
``package`` subdirectory of the ``distrubtion`` dataset. A ``builder``
subdataset, corresponding to the distribution's builder dataset, is registered
in the new hello package dataset.


Next obtain or build the source package. This example simply downloads an
existing source package.

.. code-block:: bash

   cd packages/hello
   datalad run -m "Add version 2.10-2 source package" dget -d http://deb.debian.org/debian/pool/main/h/hello/hello_2.10-2.dsc

The binary package can now be built from the ``.dsc`` using the (containerized)
build environment contained in the ``builder`` subdataset.

.. code-block:: bash

   datalad deb-build-package hello_2.10-2.dsc


Create an archive dataset
=========================



Update components
=================

Builder Dataset
---------------

Package Dataset
---------------

Distribution Dataset
--------------------

Archive Dataset
---------------

Retiring a Distribution
=======================



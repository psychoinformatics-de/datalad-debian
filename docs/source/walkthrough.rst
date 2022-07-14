.. _chap_walkthrough:

Walk-through
************

Let's take a look at the main steps and building blocks to go from source code
to a fully functional APT repository that any Debian-based machine can retrieve
and install readily executable software packages from.

This walk-through demos the command line interface of DataLad. However, an analog
Python API is provided too.


Create a distribution dataset
=============================

A distribution dataset is a DataLad superdataset that contains all necessary
components to build Debian packages for a particular distribution release.
This includes the packages' source code, and a build environment.

To create a collection of packages for a particular distribution (e.g. Debian
11, bullseye), start by creating a ``distribution`` dataset.

.. code-block:: bash

   datalad deb-new-distribution bullseye
   cd bullseye

This creates the ``distribution`` dataset "bullseye". Despite the name, the
generated dataset is still pretty generic, and not anyhow tailored to a
particular distribution yet.

Besides the distribution superdataset, a ``builder`` subdataset was created too.
It contains the subdirectories:

* ``envs``: hosts generated build environments for any number of target CPU
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

Before we can start building Debian packages, the ``builder`` subdataset must
be configured to provide one or more build environments for the respective
distribution and target CPU architecture. Start by configuring the builder for
the specific distribution release.

.. code-block:: bash

   datalad deb-configure-builder --dataset builder dockerbase=debian:bullseye

This creates a singularity container recipe for a Debian bullseye environment
based on a default template. Check the documentation of `deb-configure-builder`
for additonal configuration options, for example to enable `non-free` package
sources.

The command ``deb-bootstrap-builder`` can now be run to bootstrap the
(containerized) build environment based on the recipe just created.

.. code-block:: bash

   datalad deb-bootstrap-builder --dataset builder

The ``builder`` dataset now contains a container image that can be used for
building packages. Using singularity, the entire container acts as a single
executable that takes a Debian source package as input and builds Debian binary
packages in its environment as output. The generated container image is
registered in the ``builder`` dataset for use by the datalad-container
extension and its ``containers-run`` command.

With the builder prepared, we can safe the resulting state of the builder
in the ``distribution`` dataset.

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

Running ``datalad status`` or ``git status`` in the distribution dataset now
confirms that all components are comprehensively tracked. Inspecting the
commits of the two created datasets, and in particular those of the ``builder``
dataset, reveals how DataLad capture the exact process of the build environment
generation.


Add a package to the distribution
=================================

To add a package, start by creating a new ``package`` dataset inside of the
``distribution`` dataset.

.. code-block:: bash

   datalad deb-new-package hello

This creates a new ``package`` subdataset for a source package with the name
``hello`` under the ``packages`` subdirectory of the ``distrubtion`` dataset.
Inspecting the created dataset, we can see another ``builder`` subdataset.  In
fact, this is the ``builder`` dataset of the distribution, linked via DataLad's
dataset nesting capability.

This link serves a dual purpose. 1) It records which exact version of the
builder was used for building particular versions of a given source package,
and 2) it provides a canonical reference for updating to newer versions of the
distribution's builder, for example, after a distribution point release.

The package dataset can now be populated with a Debian source package version.
In the simplest case, a source package is merely placed into the dataset and
the addition is saved. This is what we will do in a second.

However, DataLad can capture more complex operations too, for example, using
tools like ``git-buildpackage`` to generate a source package from a "debian"
packaging branch of an upstream source code repository. An upstream code
repository can be attached as a subdataset, at the exact version needed, and
``git-buildpackage`` can be executed through ``datalad run`` to capture the
full detail of the source package generation.

For this walk-through, we download version 2.10 of the ``hello`` package from
snapshot.debian.org:

.. code-block:: bash

   cd packages/hello
   datalad run -m "Add version 2.10-2 source package" \
     dget -d -u https://snapshot.debian.org/archive/debian/20190513T204548Z/pool/main/h/hello/hello_2.10-2.dsc

The fact that we obtained the source package files via this particular download
is recorded by ``datalad run`` (run ``git show`` to see the record in the commit
message).


Build binary packages
=====================

With a Debian source package saved in a package dataset, we have all components
necessary for a Debian binary package build. Importantly, we will perform this
build in the local context of the package dataset. Although in the walk-through
the package dataset is placed inside a clone of the distribution dataset, this
particular constellation is not required. Building package is possible and support
in any (isolated) clone of the package dataset.

To build Debian binary packages we can use the ``deb-build-package`` command
parametrized with the source package's DSC filename.

.. code-block:: bash

   datalad deb-build-package hello_2.10-2.dsc

As with the download before, DataLad will capture of the full provenance of the
package build. The command will compose a call to ``datalad containers-run`` to
pass the source package on to the builder in the builder dataset. Both this
builder dataset, and the actual singularity image with the containerized build
environment is automatically obtained. This is possible, because the package
dataset exhaustively captures all information on source code to build, and
environment to build it in. Built binary packages, metadata files, and build logs
are captured in a new saved package dataset state -- precisely linking the
build inputs with the generated artifacts (again check ``git show`` for more
information).

If desired, ``deb-build-package`` can automatically update the builder dataset
prior a build. Otherwise the build is done using whatever builder environment
is registered in the dataset, for example, to re-build historical versions of
a dataset with the respective historical build environment version.

Updating a package dataset with new versions of the Debian source package, and
building binary packages from them is done be simply repeating the respective
steps.


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



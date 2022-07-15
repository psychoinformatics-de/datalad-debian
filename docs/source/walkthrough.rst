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

   bullseye/
   └── builder/
        ├── envs/
        │   └── README.md
        └── recipes/
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
for additional configuration options, for example to enable `non-free` package
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

   bullseye/
   └── builder/
        ├── envs/
        │   ├── README.md
        │   └── singularity-amd64.sif
        └── recipes/
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
building binary packages from them is done by simply repeating the respective
steps.


Create an archive dataset
=========================

With Debian source and binary packages organized in distribution and package
datasets, the remaining step is to generate a package archive that APT can use
to retrieve and install Debian packages from. A dedicated tool that can do this
is ``reprepro``, and is also the main work horse here. By applying the
previously used patterns of dataset nesting to tracking inputs, and capturing
the provenance of tool execution, when will use ``reprepro`` to ingest packages
from our distribution dataset into an APT package archive.

The first step is to create the archive DataLad dataset:

.. code-block:: bash

   # this is NOT done inside the distribution dataset
   cd ..
   datalad deb-new-reprepro-repository apt
   cd apt

We give it the name ``apt``, but this is only the name of the directory, the
dataset is created in.

::

  apt/
  ├── conf/
  │   ├── distributions
  │   └── options
  ├── distributions/
  │   └── README
  ├── README
  └── www/

The dataset is pre-populated with some content that largely reflects an
organization required by ``reprepro`` described elsewhere. Importantly,
we have to adjust the file ``conf/distributions`` to indicate the
component of the APT archive that ``reprepro`` shall generate and which
packages to accept. A minimal configuration for this demo walk-through
could be::

  Codename: bullseye
  Components: main
  Architectures: source amd64

A real-world configuration would be a little more complex, and typically
list a key to sign the archive with, etc. Once we completed the
configuration, we can safe the archive dataset:

.. code-block:: bash

   datalad save -m 'Configured archive distributions'

Now we are ready to link a distribution to the archive. This will be
the source Debian package will be incorporated into the archive from:

.. code-block:: bash

   datalad deb-add-distribution ../bullseye bullseye

The ``deb-add-distribution`` command takes two mandatory arguments:
1) a source URL for a distribution dataset, and 2) a name to register
the distribution under. In a real-world case the source URL will be
pointing to some kind of hosting service. Here we obtain it from the
root directory of the walk-through demo.

::

  apt/
  ├── conf/
  │   ├── distributions
  │   └── options
  ├── distributions/
  │   ├── bullseye/
  │   │   ├── builder/
  │   │   └── packages/
  │   │       └── hello/
  │   └── README
  ├── README
  └── www/

As we can see, the archive dataset now links the distribution dataset,
and also its package dataset, in a consistent, version tree (confirm
clean dataset state with ``datalad status``.


Ingest Debian package into an archive dataset
=============================================

With all information tracked in DataLad dataset, we can automatically
determine which packages have been added and built in any linked
distribution since the last archive update -- without having to
operate a separate upload queue. This automatic queue generation and
processing it performed by the ``deb-update-reprepro-repository``
command.

.. code-block:: bash

   datalad deb-update-reprepro-repository

Running this command on the archive dataset will fetch any updates to
all linked distribution datasets, and perform a ``diff`` with respect
to the last change recorded for the ``reprepro`` output directory
``www/``.

As we can see when running the command, no packages are ingested. That is
because when adding the Debian source package and building the binary packages
for hello version 2.10, we only saved the outcomes in the respective package
dataset. We did not register the package dataset update in the distribution
dataset. This missing step is the equivalent of authorizing and accepting a
package upload to a distribution in a centralized system.

So although there is an update of a package dataset, it will not be considered
for inclusion into the APT archive without formally registering the update
in the distribution. This is done by saving the package datasets state in
the distribution dataset

.. code-block:: bash

   cd ../bullseye
   datalad save -m "Accept hello 2.10 build for amd64"

Rerunning ``deb-update-reprepro-repository`` now does detect the package
update, automatically discovers the addition of the source package, and the
recently built binary packages, and ingest them both into the APT archive
dataset.

.. code-block:: bash

   datalad deb-update-reprepro-repository

After ``reprepro`` generated all updates to the archive, DataLad captures all
those changes and links all associated inputs and outputs of this process
in a clean dataset hierarchy. We can confirm this with ``datalad status``,
and ``git log -2`` shows the provenance information for the two internal
``reprepro`` runs involved in this APT archive update.

After the update, the working tree content of the archive dataset looks like
this::

  apt/
  ├── conf/
  │   ├── distributions
  │   └── options
  ├── db/
  │   ├── checksums.db
  │   ├── contents.cache.db
  │   ├── packages.db
  │   ├── references.db
  │   ├── release.caches.db
  │   └── version
  ├── distributions/
  │   ├── bullseye/
  │   │   ├── builder/
  │   │   └── packages/
  │   │       └── hello/
  │   │           ├── builder/
  │   │           ├── hello_2.10-2_amd64.buildinfo
  │   │           ├── hello_2.10-2_amd64.changes
  │   │           ├── hello_2.10-2_amd64.deb
  │   │           ├── hello_2.10-2.debian.tar.xz
  │   │           ├── hello_2.10-2.dsc
  │   │           ├── hello_2.10.orig.tar.gz
  │   │           ├── hello-dbgsym_2.10-2_amd64.deb
  │   │           └── logs/
  │   │               └── hello_2.10-2_20220714T073633_amd64.txt
  │   └── README
  ├── README
  └── www/
      ├── dists/
      │   └── bullseye/
      │       ├── main/
      │       │   ├── binary-amd64/
      │       │   │   ├── Packages
      │       │   │   ├── Packages.gz
      │       │   │   └── Release
      │       │   └── source/
      │       │       ├── Release
      │       │       └── Sources.gz
      │       └── Release
      └── pool/
          └── main/
              └── h/
                  └── hello/
                      ├── hello_2.10-2_amd64.deb
                      ├── hello_2.10-2.debian.tar.xz
                      ├── hello_2.10-2.dsc
                      ├── hello_2.10.orig.tar.gz
                      └── hello-dbgsym_2.10-2_amd64.deb


All added files in the archive dataset are managed by ``git-annex``, meaning
only their file identity (checksum) is tracked with Git, not their large
content. The files in ``db//`` are required for ``reprepro`` to run properly
on subsequent updates. A dedicated configuration keeps them in an "unlocked"
state for interoperability with ``reprepro``. All other files are technically
symlinks into the file content "annex" operated by ``git-annex``.

A webserver can expose the ``www/`` directory as a fully functional APT
archive. However, ``www/`` is actually a dedicated DataLad (sub)dataset, which
can also be cloned to a different location, and updates can be propagated to it
via ``datalad update`` at any desired interval.

Moreover, the ``www/`` subdataset can also be checked-out at any captured archive
update state (e.g. its state on a particular). This makes it possible to
provide any snapshot of the entire APT archive in a format that is immediately
accessible to any ``apt`` client.

In between archive dataset updates, it is not necessary to keep the distribution
and package datasets around. TO avoid accumulation of disk space demands,
these can be dropped:

.. code-block:: bash

   datalad drop -d . --what all -r distributions

Dropping is a safe operation. DataLad verifies that all file content and the
checked-out dataset state remains available from other clones when the local
clones are removed. The next run of ``deb-update-reprepro-repository`` will
re-obtain any necessary datasets automatically.

The archive dataset can now be maintained for as long as desired, by repeated
the steps for updating package datasets, registering these updates in their
distribution datasets, and running ``deb-update-reprepro-repository`` to ingest
the updates in the APT archive.

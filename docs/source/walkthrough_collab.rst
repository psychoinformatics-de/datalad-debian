
.. _chap_walkthrough_collab:

Collaborative package distribution workflow
*******************************************

This part of the document is best read after taking a look at the basic
:ref:`walk-through <chap_walkthrough>`, in which many key components are
explained -- information that will not be repeated here. Instead, here we
focus on the nature of associated workspaces and roles involved in the
collaborative maintenance and distribution of Debian packages.

Despite the different focus, the basic outcome will be the same as for the
previous walk-through: a Debian source package, built for a target Debian
release, and distributed via a reprepro-based APT archive.

As a quick reminder, several semantically different types of DataLad datasets
are used for package building and distribution/archive maintenance with
`datalad-debian`:

- **builder dataset**: DataLad dataset that tracks one or more (containerized)
  build environments, set up for use with ``datalad containers-run`` (provided by
  the DataLad `containers` extension package).

- **package dataset**: DataLad dataset that tracks versions of a single Debian
  source package, and the binary packages built for each version across all target
  architectures. This dataset also tracks the *builder dataset* with the environment
  used to build binary packages.

- **distribution dataset**: DataLad dataset that tracks any number of
  *package datasets* (one for each Debian source package included in that particular
  distribution) and a *builder dataset* with the build environment(s) used to
  build binary packages for the distribution.

- **APT-repository dataset**: DataLad dataset that tracks the content of an APT
  repository that would typically be exposed via a web-server (i.e., crucially the
  `dist/`, and `pool/` directories). For technical or legal reasons (number of
  files, split free and non-free components, etc.) this dataset may optionally have
  additional subdatasets.

- **archive dataset**: DataLad dataset that tracks an *APT-repository dataset*,
  and any number of *distribution datasets* used to populate the APT-repository
  (presently with the `reprepro` tool).


Roles
=====

Any action associated with building and distributing Debian packages with this
system involves the access to, modification and publication (`pushing`) of DataLad
datasets. Individual roles people can have are associated with different sets
of required access permissions.

- **package maintainer**: Updates a *package dataset* with new (backported)
  versions of a source package. Needs read/write access to a (particular)
  *package dataset*.

- **distribution maintainer**: Reviews and accepts/rejects new or updated
  *package datasets* (updated by a *package maintainer* or a *package
  builders*) by incorporating them into a *distribution dataset*. Needs read
  access to any *package dataset* and write access to a (particular)
  *distribution dataset*.

- **package builder**: Maintains a (containerized) build environment for a
  distribution in a *builder dataset* and updates *package datasets* with built
  binary Debian packages. Needs read/write access to a *builder dataset* and
  *package datasets*.

- **archive maintainer**: Adds *distribution datasets* to an *archive dataset*,
  and populates the *APT-repository dataset* from distribution updates. Needs
  read access to *distribution datasets* and *package datasets*, plus write
  access to *archive dataset* and *APT-repository dataset*.

- **mirror operator**: Deploys (updates of) an *APT-repository dataset* on a
  particular (additional) server infrastructure. Needs read access to the
  *APT-repository dataset*.

It is important to point out that most *write access* permissions mentioned above
do not necessarily demand actual write access to a service infrastructure.
Given the decentralized nature of Git and DataLad, any contribution can also be
handled via a pull-request-like approach that merely requires a notification of
an authorized entity with read access to the modification deposited elsewhere.


Storage and hosting
===================

The decentralized data management approach offers great flexibility regarding
choices for storing files and datasets, and environments suitable for
performing updates. For small efforts, even the simplistic approach of using a
monolithic directory (as shown in the :ref:`initial walk-through
<chap_walkthrough>`) may be good enough. However, larger operations involving
multiple people and different levels of trust benefit from a stricter
compartmentalization.

- **APT-repository dataset checkout**: This location is typically exposed via a
  web-server and the APT client facing end of the system. In addition to being
  used by APT for its normal operation, it can also be (git/datalad) cloned
  from (including historic version), and is capable of hosting and providing
  previous versions of any repository content in a debian-snapshot like
  fashion. Only *archive maintainer* need write access, while read access
  is typically "public" or anonymous.

- **Hosting of archive/APT-repository datasets**: Especially for large
  archives, update operations of these two datasets can be expensive, and
  generally a full (nested) checkout is required for any modification.
  Consequently, it typically makes sense to maintain a long-lived checkout
  location for them (possibly in a way that allows for directly exposing the
  checkout of the *APT-repository subdataset* via a web server.

- **Hosting of distribution datasets**: These need to have read access for all
  maintainer roles, and write access for *distribution maintainers* only. Larger
  efforts might benefit from a proper Git hosting solution in order to be able
  to process incoming package update requests via a pull-request or issue
  tracking system.

- **Hosting of package datasets**: *Package maintainers* need to deposit source
  and binary package files in a way that enables *package builders* and
  *archive maintainers* to retrieve them. Any datalad-supported sibling type can
  be used, including git-annex aware systems like GIN or RIA-stores, or dual
  hosting approaches with a Git-hoster for the dataset and a (cloud) storage
  solution for file content.

- **Hosting of builder datasets**: The requirement for hosting are largely
  identical to those of *package datasets*, except that the build environments
  generally should be accessible to any *package maintainer* too.


Workspaces for particular actions
=================================

The following sections show concrete examples of workflows suitable for
collaboratively working with this system. Given the available flexibility these
cannot be considered as one-size-fits-all, and there will be hints on possible
different approaches that may be better from some.

Importantly, we will focus on a "clean-desk" approach that minimized the number
of long-lived locations that imply maintenance and coordination costs.

..
  - distds: gitlab for review and flexible permission management
  - builderds: bulk storage with anon https-read and ssh-push by build-maintainer
  - packageds: accept for review from any place, and then push clone to bulk storage by dist-maintainer (also enables automated update with binaries by build-maintainer)
  - apt-repo/archive dataset: long-lived checkout (where?)


Create a distribution dataset with a package builder
----------------------------------------------------

We start with standard preparation steps of a *distribution dataset*: create,
configure and bootstrap builder, save.

.. code-block:: bash

   datalad deb-new-distribution bullseye
   datalad -C bullseye deb-configure-builder --dataset builder dockerbase=debian:bullseye
   datalad -C bullseye deb-bootstrap-builder --dataset builder
   datalad -C bullseye save -d . --message "Update distribution builder" builder


We are not planning to keep the just created dataset around in this location,
but rather push them to services or locations that are more appropriate for
collaboration or archiving.  Hence we need to inform the dataset annexes that
it is not worth tracking this location.  This is not needed for the
*distribution dataset* itself, it has no annex.

.. code-block:: bash

   datalad -C bullseye/ foreach-dataset --subdatasets-only git annex dead here

We will place the two datasets, *distribution and builder dataset* in two
different locations, with different access permissions matching the differences
in target audiences.

For the sake of keeping this example working as a self-contained copy/paste demo,
we are only using "RIA"-type DataLad siblings. However, this is not a requirement
and alternatives will be pointed out below.

The *distribution dataset* is put in a place suitable for collaboration. The
``create-sibling-ria`` call below creates a dataset store and places a dataset
clone in it, configured for group-shared access (here using the ``dialout``
group, simply because it likely is a group that a user trying the demo out is
already part of; in a real-world deployment this might be
``bullseye-maintainers``). More typical would be to use
``create-sibling-gitlab`` or ``create-sibling-github`` (or similar) to
establish a project on a proper Git hosting service that also provides an issue
tracker and pull-request management support to streamline collaborative
maintenance.

.. code-block:: bash

   datalad -C bullseye/ create-sibling-ria -s origin --new-store-ok \
     --shared group --group dialout --alias dist-bullseye \
     ria+file:///tmp/wt/gitlab

The *builder dataset* is tracking large-ish build environment images, and needs
a place to push this file content too. Moreoever, it likely makes sense to limit
push access to a particular group of people. For this demo, we simply use a
different RIA store, with a different group setting (``floppy`` is again a
random-but-likely-existing choice).

.. code-block:: bash

   datalad -C bullseye/builder/ create-sibling-ria -s origin --new-store-ok \
     --shared group --group floppy --alias builder-bullseye \
     ria+file:///tmp/wt/internal

With the remote sibling created, we can push the datasets (recursively, i.e., both
together), and drop them entirely from our workspace.

.. code-block:: bash

   datalad -C bullseye/ push -r --to origin
   datalad drop --what all -r -d bullseye

``drop`` is checking that nothing unrecoverable is left before wiping out the
repositories. Cleaning the workspace completely ensure that any and all content
is placed in proper hosting/archive solutions.


Create an archive dataset
-------------------------

An *archive dataset* has different hosting demands. The ``reprepro`` tool
essentially requires the full work tree to be present at all times. For large
APT-archives even a clone may take considerable time. Hence we are create the
archive dataset in the location where is would/could live semi-persistently.

We add our *distribution dataset* from the collaboration-focused dataset store
(GitLab placeholder). The need not live on the same machine. Any source URL
that DataLad supports is suitable. The *distribution dataset* clone inside
the *archive dataset* need not stay there permanently, but can be dropped and
reobtained as needed.


.. code-block:: bash

   datalad deb-new-reprepro-repository archive
   datalad deb-add-distribution -d archive/ ria+file:///tmp/wt/gitlab#~dist-bullseye bullseye

   # minimalistic reprepro config
   cat << EOT > archive/conf/distributions
   Codename: bullseye
   Components: main
   Architectures: source amd64
   EOT
   datalad save -d archive


Add a package to a distribution
-------------------------------

With the *archive dataset* ready, we need to start populating the *distribution
dataset*. Importantly, this need not be done in the existing clone inside the
*archive datatset*, but can be performed in an ephemeral workspace.

We make a temporary clone, and add a *package dataset* to it.

.. code-block:: bash

   datalad clone ria+file:///tmp/wt/gitlab#~dist-bullseye dist
   datalad deb-new-package -d dist demo

This new *package dataset* is another item that a group of *package maintainers*
could collaborate on, hence we put this on "GitLab" too.

.. code-block:: bash

   datalad -C dist/packages/demo/ create-sibling-ria -s origin --alias pkg-demo \
      ria+file:///tmp/wt/gitlab

When a *distribution maintainer* needs to pull an update, we want them to know
about this "upstream" location, hence register it as the subdataset URL.

.. code-block:: bash

   datalad subdatasets -d dist \
     --set-property url "$(git -C dist/packages/demo remote get-url origin)" \
     dist/packages/demo

As before, this initial location of the newly created *package dataset* is of
no relevance, so we tell the dataset to forget about it, push everything to the
respective hosting (incl. the update of the *distribution dataset* with the
addition), and clean the entire workspace.

.. code-block:: bash

   git -C dist/packages/demo annex dead here
   datalad -C dist push --to origin -r
   datalad drop --what all -r -d dist


Update a package
----------------

Updating a *package dataset* only requires access to the particular *package
dataset* to be updated, and can, again, be done in an ephemeral workspace.
Here we clone via SSH to indicate that this could be performed anywhere.

.. code-block:: bash

   datalad clone --reckless ephemeral ria+ssh://localhost/tmp/wt/gitlab#~pkg-demo pkg

A key task of updating a *package dataset* is adding a new source package version.
This can involve arbitrary procedures. Here we simply download a ready-made
source package from Debian. Alternatively, a source package could be generated
via `git-buildpackage` from a linked packaging repo, or something equivalent.

.. code-block:: bash

   datalad -C pkg run \
     -m "Add version 2.10-2 source package" \
     dget -d -u \
     https://snapshot.debian.org/archive/debian/20190513T204548Z/pool/main/h/hello/hello_2.10-2.dsc

Using ``datalad run`` automatically tracks the associated provenance and saves
the outcome, so we can, again, ``push`` the result and clean the entire workspace.

.. code-block:: bash

   datalad -C pkg push
   datalad drop --what all -r -d pkg


Update a package in a distribution
----------------------------------

*Package maintainers* updating a *package dataset* does not automatically
alter the state of the package in the context of a particular distribution.
*Package maintainers* need to inform the *distribution maintainers* about
their intention to update a package (e.g., via an issue filed, or a post-update
hook trigger, etc.). Once the to-be-updated package is known, as *distribution
maintainer* can perform the update in an ephemeral workspace.

The make a temporary clone of the *distribution dataset*, obtain the
respective *package dataset*, update it from the upstream location on record
(or a new one that was communicated by some external means).


.. code-block:: bash

   datalad clone --reckless ephemeral ria+file:///tmp/wt/gitlab#~dist-bullseye dist
   datalad -C dist get -n packages/demo/
   datalad update -d dist -r --how reset packages/demo/

This changes the recorded state of the *package dataset* within the
*distribution dataset*, equivalent to an update of a versioned link.

It is likely advisable to not rely on the upstream location of the *package
dataset* being persistent. A *distribution maintainer* can hence push
the *package dataset* to some trusted, internal infrastructure too, in order
to make the distribution effort self-sufficient. For this demo, we push to
the internal RIA store, but again, any DataLad sibling type would work in
principle.


.. code-block:: bash

   datalad -C dist/packages/demo create-sibling-ria -s internal \
     --existing reconfigure --shared group --group floppy \
     --alias pkg-demo \
     ria+file:///tmp/wt/internal
   datalad -C dist/packages/demo push --to internal

All that remains to be done, is to also push the *distribution dataset*
back to "GitLab" and clean the workspace.

.. code-block:: bash

   datalad -C dist push
   datalad drop --what all -r -d dist


Build binary packages for a distribution
----------------------------------------

Building binary packages from source package can be done by *package
maintainers* and only requires the *package dataset*, because it also links the
*builder dataset* for a distribution. With the provenance tracking provided by
DataLad *distribution maintainers* could even programmatically verify that a
paricular binary package was actually built with the correct environment, and
even whether such a build is reproducible. However, builds are also often done
by automated systems.

Such a system needs to perform the following steps, in a temporary workspace:
Clone the package dataset (here we take it from the trusted internal storage
solution

.. code-block:: bash

   datalad clone --reckless ephemeral ria+ssh://localhost/tmp/wt/internal#~pkg-demo pkg

Once the binary packages are built, we want to push them to the internal storage
too. We configure a publication dependency to make this happen automatically
later on.

.. code-block:: bash

   datalad -C pkg siblings configure -s origin --publish-depends internal-storage

Now the package can be built. It may be desirable to use automatically update
the build environment prior building in some cases. Here we use the exact builder
version linked to the *package dataset*.

.. code-block:: bash

   datalad -C pkg/ deb-build-package hello_2.10-2.dsc

Once the build succeeded, the outcome can be pushed and the workspace cleaned up.

.. code-block:: bash

   datalad -C pkg push
   # https://github.com/psychoinformatics-de/datalad-debian/issues/118
   sudo rm -rf /tmp/wt/pkg/builder/cache
   datalad drop --what all -r -d pkg


Update a package with additional builds in a distribution
---------------------------------------------------------

Updating a *package dataset* within a *distribution dataset*, because
additional binary packages were built by a *build mainatiner* is similar to an
update due to a new source package added by a *package maintainer*. Again
possible in a temporary workspace.

.. code-block:: bash

   datalad clone --reckless ephemeral ria+ssh://localhost/tmp/wt/gitlab#~dist-bullseye dist

The main difference is that we instruct DataLad to retrieve the respective
*package dataset* not from the "upstream" location, but from internal storage.

.. code-block:: bash

   # configure to only retrieve package datasets from trusted storage
   # must not be ria+file:// due to https://github.com/datalad/datalad/issues/6948
   DATALAD_GET_SUBDATASET__SOURCE__CANDIDATE__100internal='ria+ssh://localhost/tmp/wt/internal#{id}' \
     datalad -C dist get -n packages/demo/

This change makes sure that we need not worry about unapproved upstream
modification showing up at this stage.

Now we can update, push, and clean up as usual, and end with an empty
workspace.

.. code-block:: bash

   datalad update -d dist -r --how reset packages/demo/
   datalad -C dist push
   datalad drop --what all -r -d dist


Ingest package updated into an archive dataset
----------------------------------------------

We can also use the same trick to only pull *package datasets* from
internal storage when updating the *archive dataset*

.. code-block:: bash

   DATALAD_GET_SUBDATASET__SOURCE__CANDIDATE__100internal='ria+file:///tmp/wt/internal#{id}' \
     datalad -C archive deb-update-reprepro-repository

As explained in the intial :ref:`walk-through <chap_walkthrough>` this step
automatically detects changes in the linked distributions, and ingests them
into the archive. Any and all *distribution datasets* could be dropped again
afterwards to save on storage demands.

Recreate (new) archive dataset from scratch
-------------------------------------------

The order in which the steps above where presented is not strictly defined.
Most components can (re)created at a later or different point in time.

Here is an example of how an *archive dataset* can be created and populated
from scratch, given a *distribution dataset*.

.. code-block:: bash

   # create new archive
   datalad deb-new-reprepro-repository archive
   # pull distribution dataset from collab space
   datalad deb-add-distribution -d archive/ \
     ria+file:///tmp/wt/gitlab#~dist-bullseye bullseye
   # configure reprepro is needed
   cat << EOT > archive/conf/distributions
   Codename: bullseye
   Components: main
   Architectures: source amd64
   EOT
   datalad save -d archive
   # configure distribution dataset clone to always pull its package
   # (sub)datasets from internal storage
   datalad configuration -d archive/distributions/bullseye \
     --scope local \
     set 'datalad.get.subdataset-source-candidate-100internal=ria+file:///tmp/wt/internal#{id}'
   # ingest all packages
   datalad -C archive deb-update-reprepro-repository

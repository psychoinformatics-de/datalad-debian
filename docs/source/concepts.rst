Concepts & Terms
****************

Components
==========

All components are implemented in the form of DataLad datasets, interconnected
(via super-subdataset relationships) to express dependencies. For more
information about DataLad's super-subdataset relationships, please refer to the
`DataLad Handbook`_.

``builder`` dataset: environments (e.g. Singularity images) to build binary
packages from source packages using a containerized pipeline for a single target
distribution.

``package`` dataset: source and binary *Debian* packages for a single piece
of software specific to a distribution major release. Contains a ``builder``
dataset, attached as a subdataset, for the respective distribution.

``distribution`` dataset: collection of ``package`` datasets built for a specific
distribution release (e.g. Debian 10). Contains a single ``builder`` subdataset
for the respective distribution release.

``archive`` dataset: Debian package archive for deployment on a webserver as an
apt repository.  Contains any number of ``distribution`` datasets as subdatasets
that are used as sources to populate the archive.

.. _DataLad Handbook: https://handbook.datalad.org/en/latest/basics/101-180-FAQ.html#what-is-the-difference-between-a-superdataset-a-subdataset-and-a-dataset




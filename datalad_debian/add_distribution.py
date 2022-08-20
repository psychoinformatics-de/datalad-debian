import logging

from datalad.distribution.dataset import (
    EnsureDataset,
    datasetmethod,
    require_dataset,
)
from datalad.interface.base import (
    Interface,
    build_doc,
)
from datalad.interface.utils import (
    eval_results,
)
from datalad.support.constraints import (
    EnsureNone,
    EnsureStr,
)
from datalad.support.param import Parameter

lgr = logging.getLogger('datalad.debian.add_distribution')


@build_doc
class AddDistribution(Interface):
    """Add a distribution dataset to a Debian archive repository dataset
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify the Debian archive repository dataset to add the
            distribution to""",
            constraints=EnsureDataset() | EnsureNone()),
        source=Parameter(
            args=("source",),
            metavar='SOURCE',
            doc="""URL, DataLad resource identifier, local path or instance of
            distribution dataset to be added""",
            constraints=EnsureStr()),
        name=Parameter(
            args=('name',),
            metavar='NAME',
            doc="""name to add the distribution dataset under
            (directory distributions/<name>). The name should equal the
            codename of a configured distribution in the archive. If multiple
            distribution datasets shall target the same distribution, their
            name can append a '-<flavor-label>' suffix to the distribution
            codename.""",
            constraints=EnsureStr() | EnsureNone()),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_add_distribution')
    @eval_results
    def __call__(source, name, *, dataset=None):
        # - dataset must be distribution-type (needs to have a builder)
        # - name must be unique (auto-ensured)

        archive_ds = require_dataset(dataset)

        # we put all of them in a dedicated directory to have an
        # independent namespace for them that does not conflict with other
        # components of the distribution dataset
        dist_ds = archive_ds.pathobj / 'distributions' / name
        if dist_ds.exists():
            raise ValueError(f"Target path {dist_ds} already exists. "
                             "Remove first, or choose a different name.")

        # TODO we likely want to change this to a more careful implementation
        # following the pattern of `new-package`
        # - clone without registering
        # - inspect for sanity, is this a distribution dataset that was cloned
        # - save and inject the source URL into the .gitmodules record
        yield from archive_ds.clone(
            source,
            path=dist_ds,
            result_filter=None,
            result_xfm=None,
            result_renderer='disabled',
            return_type='generator',
            # we leave the flow-control to the caller
            on_failure='ignore',
        )

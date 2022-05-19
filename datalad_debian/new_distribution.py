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

lgr = logging.getLogger('datalad.debian.new_distribution')


@build_doc
class NewDistribution(Interface):
    """Create a new distribution dataset
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a dataset whose configuration to inspect
            rather than the global (user) settings""",
            constraints=EnsureDataset() | EnsureNone()),
        path=Parameter(
            args=("path",),
            nargs='?',
            metavar='PATH',
            doc="""path where the dataset shall be created, directories
            will be created as necessary. If no location is provided, a dataset
            will be created in the location specified by [PY: `dataset`
            PY][CMD: --dataset CMD] (if given) or the current working
            directory. Either way the command will error if the target
            directory is not empty. Use [PY: `force` PY][CMD: --force CMD] to
            create a dataset in a non-empty directory.""",
            # put dataset 2nd to avoid useless conversion
            constraints=EnsureStr() | EnsureDataset() | EnsureNone()),
        force=Parameter(
            args=("-f", "--force",),
            doc="""enforce creation of a dataset in a non-empty directory""",
            action='store_true'),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_new_distribution')
    @eval_results
    def __call__(path=None, *, dataset=None, force=False):
        dist_ds = None

        from datalad.api import create
        for res in create(
                dataset=dataset,
                path=path,
                force=force,
                # critical, otherwise create() throws any errors away
                # https://github.com/datalad/datalad/issues/6695
                result_filter=None,
                result_xfm=None,
                result_renderer='disabled',
                return_type='generator',
                on_failure='ignore',
        ):
            # we yield first to make external flow control possible
            yield res
            if result_matches(res,
                              action='create', type='dataset',
                              status=('ok', 'notneeded')):
                dist_ds = require_dataset(res['path'])
        if not dist_ds:
            # we cannot continue, something went wrong with create, and
            # should have been communicated already, log to ensure leaving
            # a trace
            lgr.debug('Distribution dataset did not materialize, stopping')
            return

        # ensure the builder dataset is where it needs to be
        yield from dist_ds.create(
            path='builder',
            force=force,
            cfg_proc='debianbuilder',
            # critical, otherwise create() throws any errors away
            # https://github.com/datalad/datalad/issues/6695
            result_filter=None,
            result_xfm=None,
            result_renderer='disabled',
            return_type='generator',
            # we leave the flow-control to the caller
            on_failure='ignore',
        )


def result_matches(res, **kwargs):
    # special internal type that could not possibly come from outside
    # which we can use to streamline our tests here
    class NotHere():
        pass

    for k, v in kwargs.items():
        if not isinstance(v, (list, tuple)):
            # normalize for "is in" test
            v = (v,)
        if res.get(k, NotHere) not in v:
            # either `k` was not in `res, or the value does not match
            return False
    return True

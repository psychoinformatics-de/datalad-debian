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

from datalad_debian.utils import result_matches


lgr = logging.getLogger('datalad.debian.new_distribution')


@build_doc
class NewDistribution(Interface):
    """Create a new distribution dataset

    A typical distribution dataset contains a 'builder' subdataset with one or
    more build environments, and a package subdirectory with one subdataset per
    Debian package.
    This command creates the initial structure: A top-level dataset
    under the provided path and a configured 'builder' subdataset underneath.
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

    _examples_ = [
        dict(text="Create a new distribution dataset called 'bullseye' in the "
             "current directory",
             code_py="deb_new_distribution(path='bullseye')",
             code_cmd="datalad deb-new-distribution bullseye"),
    ]

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
                # a distribution dataset is just a container for
                # (package) subdatasets
                annex=False,
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
        for res in dist_ds.create(
            path='builder',
            force=force,
            # critical, otherwise create() throws any errors away
            # https://github.com/datalad/datalad/issues/6695
            result_filter=None,
            result_xfm=None,
            result_renderer='disabled',
            return_type='generator',
            # we leave the flow-control to the caller
            on_failure='ignore',
        ):
            yield res
            if result_matches(res,
                              action='create', type='dataset',
                              status=('ok', 'notneeded')):
                # configure the debian builder
                builder_ds = require_dataset(res['path'])
                repo = builder_ds.repo
                if not builder_ds:
                    lgr.debug('Builder dataset did not materialize, stopping')
                    return
                to_save = []

                for f, c in (
                        (builder_ds.pathobj / 'recipes' / 'README.md',
                         "This directory contains the recipes for all build"
                         "pipeline images.\n"),
                        (builder_ds.pathobj / 'envs' / 'README.md',
                         "This directory contains build pipeline images.\n"),
                        (builder_ds.pathobj / 'init' / 'README.md',
                         "Anything in this directory is copied\n"
                         "into the root of the build environment.\n"
                         "Executables placed into `/finalize` inside the\n"
                         "build environment are ran at the very end of\n"
                         "the bootstrapping process.\n"),
                ):
                    if not f.exists():
                        f.parent.mkdir(exist_ok=True)
                        f.write_text(c)
                        to_save.append(f)

                for f, a in (
                        # all recipes go into Git
                        (repo.pathobj / 'recipes' / '.gitattributes',
                         [('*', {'annex.largefiles': 'nothing'})]),
                        # we might want to save these in unlocked state
                        # but for now simply put them in git
                        (repo.pathobj / 'init' / '.gitattributes',
                         [('*', {'annex.largefiles': 'nothing'})]),
                        (repo.pathobj / 'envs' / '.gitattributes',
                         [('*.md', {'annex.largefiles': 'nothing'})]),
                ):
                    if not f.exists():
                        repo.set_gitattributes(a, f)
                        to_save.append(f)

                # ignore a cache/ dir, may not be used by all setups,
                # but adds a little convenience for those who do
                gitignore = repo.pathobj / '.gitignore'
                if not gitignore.exists():
                    gitignore.write_text("cache\n")
                    to_save.append(gitignore)

                yield from builder_ds.save(
                    path=to_save,
                    message='Debian builder dataset setup',
                    result_xfm=None,
                    return_type='generator',
                    result_renderer='disabled',
                )

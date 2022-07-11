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


ckwa = dict(
    result_xfm=None,
    result_renderer='disabled',
    return_type='generator',
    # we leave the flow-control to the caller
    on_failure='ignore',
)


@build_doc
class NewRepreproRepository(Interface):
    """Create a new (reprepro) package repository dataset
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
    @datasetmethod(name='deb_new_reprepro_repository')
    @eval_results
    def __call__(path=None, *, dataset=None, force=False):
        reprepro_ds = None
        archive_ds = None

        from datalad.api import create
        for res in create(
                dataset=dataset,
                path=path,
                force=force,
                # critical, otherwise create() throws any errors away
                # https://github.com/datalad/datalad/issues/6695
                result_filter=None,
                **ckwa
        ):
            # we yield first to make external flow control possible
            yield res
            if result_matches(res,
                              action='create', type='dataset',
                              status=('ok', 'notneeded')):
                reprepro_ds = require_dataset(res['path'])
        if not reprepro_ds:
            # we cannot continue, something went wrong with create, and
            # should have been communicated already, log to ensure leaving
            # a trace
            lgr.debug('Reprepro dataset did not materialize, stopping')
            return

        # and the same for the debian/ subdataset (the actual package archive)
        for res in reprepro_ds.create(
            path='www',
            force=force,
            # critical, otherwise create() throws any errors away
            # https://github.com/datalad/datalad/issues/6695
            result_filter=None,
            **ckwa
        ):
            yield res
            if result_matches(res,
                              action='create', type='dataset',
                              status=('ok', 'notneeded')):
                archive_ds = require_dataset(res['path'])
        if not archive_ds:
            lgr.debug('Archive dataset did not materialize, stopping')
            return

        yield from _setup_reprepro_ds(reprepro_ds)


def _setup_reprepro_ds(ds):
    repo = ds.repo
    # destination for the reprepro config
    (ds.pathobj / 'conf').mkdir()
    # we want the config and documentation to be in git
    repo.call_annex([
        'config', '--set', 'annex.largefiles',
        'exclude=conf/* and exclude=README/* and exclude=*/README'])
    # establish basic config for repository and reprepro behavior
    (ds.pathobj / 'conf' / 'options').write_text(conf_opts_tmpl)
    # the DB files written and read by reprepro need special handling
    # we need to keep them unlocked (for reprepro to function normally
    # without datalad), but we also do not want them in git, and we also
    # cannot fully ignore them: make sure the anything in db/ is tracked
    # but always unlocked
    repo.call_annex([
        'config', '--set', 'annex.addunlocked', 'include=db/*'])

    dist_readme = ds.pathobj / 'distributions' / 'README'
    dist_readme.parent.mkdir(parents=True, exist_ok=True)
    dist_readme.write_text(dist_subds_readme)
    yield from ds.save(
        path=['conf', 'repo', dist_readme],
        message='Basic reprepro setup',
        **ckwa
    )

    # place some default repo config to make obvious what needs to go
    # where
    dist_conf_f = ds.pathobj / 'conf' / 'distributions'
    if not dist_conf_f.exists():
        dist_conf_f.write_text(dist_config_tmpl)
        lgr.info('Please complete configuration draft at %s', dist_conf_f)


conf_opts_tmpl = """\
# we want repropro to ask for a key passphrase and not just die
ask-passphrase
# tell reprepro where the repository root is (root of the subdataset)
outdir +b/www
"""

dist_config_tmpl = """\
# Minimal configuration placeholder
# see https://wiki.debian.org/DebianRepository/SetupWithReprepro
# for more information on how to complete the configuration

Codename: <distribution codename>
Components: main
Architectures: amd64
SignWith: <signing key ID>
"""

dist_subds_readme = """\
Distribution datasets with packages to be included in the package
repository are placed into this directory as subdatasets.
"""

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

lgr = logging.getLogger('datalad.debian.new_package')


@build_doc
class NewPackage(Interface):
    """Create a new package dataset
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a distribution dataset to add the package to""",
            constraints=EnsureDataset() | EnsureNone()),
        name=Parameter(
            args=('name',),
            metavar='NAME',
            doc="""name of the package to add to the distribution""",
            constraints=EnsureStr() | EnsureNone()),
        force=Parameter(
            args=("-f", "--force",),
            doc="""enforce creation of a package dataset in a
            non-empty directory""",
            action='store_true'),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_new_package')
    @eval_results
    def __call__(name, *, dataset=None, force=False):
        # - dataset must be distribution-type (needs to have a builder)
        # - name must be unique (auto-ensured)

        dist_ds = require_dataset(dataset)
        builder_info = dist_ds.subdatasets(
            path='builder',
            result_renderer='disabled',
            return_type='item-or-list',
            # we leave the flow-control to the caller
            on_failure='ignore',
        )
        # we must have one result for the must-have builder dataset
        if builder_info is None:
            yield dict(
                action='deb_new_package',
                status='error',
                path=dist_ds,
                message=(
                    "Failed to find a builder subdataset underneath %s. "
                    "Make sure to run the command in a distribution "
                    "superdataset, with a builder configured and created "
                    "by datalad deb-configure-builder and datalad "
                    "deb-bootstrap-builder.", dist_ds
                )
            )
            return
        # unsure if this can ever happen, but if it does, report our confusion
        if not isinstance(builder_info, dict):
            raise RuntimeError("Internal error: It seems as if multiple "
                               "builder subdatasets were found, or they were "
                               "reported in an unexpected structure.")

        # we put all of them in a dedicated directory to have an
        # independent namespace for them that does not conflict with other
        # components of the distribution dataset
        pkg_ds = dist_ds.pathobj / 'packages' / name

        # create a (new) subdataset for the package
        from datalad.api import create
        yield from create(
            # we do not want to register the subdataset right away, in order to
            # avoid multiple commits in the distribution dataset when
            # configuring the package dataset
            # `create` should nevertheless ensure that no `name` that conflicts
            # with a known package makes it through
            dataset=None,
            path=pkg_ds,
            force=force,
            #cfg_proc='debianpkg',
            # critical, otherwise create() throws any errors away
            # https://github.com/datalad/datalad/issues/6695
            result_filter=None,
            result_xfm=None,
            result_renderer='disabled',
            return_type='generator',
            # we leave the flow-control to the caller
            on_failure='ignore',
        )

        # and this point the dataset must exist
        pkg_ds = require_dataset(pkg_ds)

        # register the distribution's builder dataset
        # this implementation duplicates some parts of
        # GitRepo._save_add_submodules()
        pkg_repo = pkg_ds.repo
        # we register whatever state of the distribution's builder dataset
        # in the package dataset too -- also overwriting any previous state
        # in case of a --force run
        pkg_repo.call_git([
            'update-index', '--add', '--replace', '--cacheinfo', '160000',
            builder_info['gitshasum'],
            'builder',
        ])

        # now we also transfer any subdataset properties (ID, URL, etc.)
        builder_subm_props = {
            k[10:]: v for k, v in builder_info.items()
            if k.startswith('gitmodule_')
        }
        builder_subm_props['path'] = 'builder'
        if builder_subm_props['url'] == './builder':
            # this cannot possibly resolve, point to the would-be location
            # of the builder dataset, assuming we are in a monolithic
            # checkout of the distribution dataset. This is just a better
            # guess. For robust behavior, the distribution dataset should
            # really provide a proper URL for the builder dataset.
            builder_subm_props['url'] = '../../builder'
        # and write them to .gitmodules
        # TODO this will presently kill any other content
        # in case of a --force run; could be made more convenient
        from datalad.config import write_config_section
        with (pkg_repo.pathobj / '.gitmodules').open('w') as gmf:
            write_config_section(
                gmf, 'submodule', 'builder', builder_subm_props,
            )
        # absent submodules are expected to have an empty mountpoint
        # in a clean repo
        (pkg_repo.pathobj / 'builder').mkdir(exist_ok=True)

        # do not use top-level `save()`, because its checks
        # will choke on this special case of injecting an absent
        # submodule
        pkg_repo.call_git(['add', '.gitmodules'])
        pkg_repo.commit(msg='Register distribution builder')

        # while the previous submodule/dataset setup did not cause accessible
        # results, the next save() of the distribution dataset will and must.
        # it will communicate whether any changes where done
        yield from dist_ds.save(
            pkg_ds.pathobj,
            message='New stuff',
            result_renderer='disabled',
            return_type='generator',
            on_failure='ignore',
        )

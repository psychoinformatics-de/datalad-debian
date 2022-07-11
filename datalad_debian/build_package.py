import logging
from pathlib import Path

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
from datalad.runner import (
    Runner,
    StdOutCapture,
)
from datalad.support.param import Parameter

lgr = logging.getLogger('datalad.debian.build_package')


@build_doc
class BuildPackage(Interface):
    """Build binary packages
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""ahyeah! package dataset!""",
            constraints=EnsureDataset() | EnsureNone()),
        dsc=Parameter(
            args=('dsc',),
            metavar='DSC',
            doc="""damn!""",
            constraints=EnsureStr() | EnsureNone()),
        update_builder=Parameter(
            args=("--update-builder",),
            doc="""why not?!""",
            action='store_true'),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_build_package')
    @eval_results
    def __call__(dsc, *, dataset=None, update_builder=False):
        dsc = Path(dsc)

        pkg_ds = require_dataset(dataset)

        if not dsc.exists() and not dsc.is_symlink():
            # maybe this is just the dsc filename, inside the `dataset`
            dsc = pkg_ds.pathobj / dsc

        # we need to make sure the DSC is around to be able to parse it
        yield from pkg_ds.get(
            dsc,
            result_renderer='disabled',
            return_type='generator',
            # leave flow-control to caller
            on_failure='ignore',
        )

        srcpkg_files = [
            str(Path(p).relative_to(pkg_ds.pathobj))
            if Path(p).is_absolute() else p
            for p in Runner().run(
                ['dcmd', str(dsc)],
                protocol=StdOutCapture)['stdout'].strip().split('\n')
        ]

        print(srcpkg_files)
        # TODO this could later by promoted to an option to support more than
        # singularity
        cfgtype = 'singularity'

        # figure out which architecture we will be building for
        binarch = Runner().run(
            ['dpkg-architecture', '-q', 'DEB_BUILD_ARCH'],
            protocol=StdOutCapture)['stdout'].strip()

        buildenv_name = f"{cfgtype}-{binarch}"

        # needed, even when no `update_builder` is intended because we want to
        # establish a cache dir inside the build dataset
        # (at least for now)
        yield from pkg_ds.get(
            'builder',
            get_data=False,
            result_renderer='disabled',
            return_type='generator',
            # leave flow-control to caller
            on_failure='ignore',
        )

        # optionally pull in the latest builder updates
        if update_builder:
            yield from pkg_ds.update(
                path='builder',
                # we want to slavishly follow the distribution setup
                how='reset',
                recursive=True,
                recursion_limit=1,
                result_renderer='disabled',
                return_type='generator',
                # leave flow-control to caller
                on_failure='ignore',
            )

            yield from pkg_ds.save(
                'builder',
                message='Updated builder',
                result_renderer='disabled',
                return_type='generator',
                on_failure='ignore',
            )

        # TODO this should really be the task of a shim that
        # establishes the conditions for the singularity image to
        # function, and it should be registered with `containers-run`
        # making all of this obsolete
        for p in (
                pkg_ds.pathobj / 'builder' / 'cache' / 'var' / 'cache' / 'apt',
                pkg_ds.pathobj / 'builder' / 'cache' / 'var' / 'lib' / 'apt'):
            p.mkdir(exist_ok=True, parents=True)

        # users might have forgotten to bootstrap the builder. Downstream, this
        # would result in no containers being found. We fail early & informative
        cname = f"builder/{buildenv_name}"
        known_containers = pkg_ds.containers_list(
            recursive=True,
            result_renderer='disabled',
            return_type='list',
            on_failure='ignore'
        )
        if cname not in [c['name'] for c in known_containers]:
            yield dict(
                action='deb_build_package',
                status='impossible',
                path='pkg_ds',
                message=(
                    "Couldn't find the required builder container %s. Forgot to "
                    "bootrap it?", cname
                )

            )
            return

        yield from pkg_ds.containers_run(
            # needs to go in relative, because it is interpreted inside the
            # (containerized) buildenv
            dsc.relative_to(pkg_ds.pathobj) if dsc.is_absolute() else dsc,
            container_name=cname,
            message=f"Build {dsc.name} for {binarch}",
            inputs=srcpkg_files,
            # we do not need to declare outputs,
            # the debian tooling can handle existing files
            #output=
            result_renderer='disabled',
            return_type='generator',
            on_failure='ignore',
        )

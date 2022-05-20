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
from datalad.runner import (
    Runner,
    StdOutCapture,
)
from datalad.support.constraints import (
    EnsureNone,
)
from datalad.support.param import Parameter

lgr = logging.getLogger('datalad.debian.bootstrap_builder')


@build_doc
class BootstrapBuilder(Interface):
    """Bootstrap a build environment
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a distribution dataset to add the package to""",
            constraints=EnsureDataset() | EnsureNone()),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_bootstrap_builder')
    @eval_results
    def __call__(*, dataset=None):
        # TODO this could later by promoted to an option to support more than
        # singularity
        cfgtype = 'singularity'

        builder_ds = require_dataset(dataset)

        # figure out which architecture we will be building for
        binarch = Runner().run(
            ['dpkg-architecture', '-q', 'DEB_BUILD_ARCH'],
            protocol=StdOutCapture)['stdout'].strip()

        buildenv_name = f"{cfgtype}-{binarch}"

        recipe = None
        for p in (builder_ds.pathobj / 'recipes' / f"{cfgtype}-{binarch}",
                  builder_ds.pathobj / 'recipes' / f"{cfgtype}-any"):
            if p.exists():
                recipe = p
                break
        if recipe is None:
            raise RuntimeError(
                "Cannot locate build environment recipe for "
                f"{cfgtype}({binarch})")

        # TODO allow for other types of environments
        buildenv = Path('envs', f"{buildenv_name}.sif")

        yield from builder_ds.run(
            # TODO allow for other means of privilege escalation
            # TODO allow for other means to bootstrap
            "sudo singularity build {outputs} {inputs}",
            inputs=[str(recipe.relative_to(builder_ds.pathobj))],
            outputs=[str(buildenv)],
            result_renderer='disabled',
            return_type='generator',
            # give control flow to caller
            on_failure='ignore',
        )

        buildenv_callfmt = \
            'singularity run ' \
            '--bind builder/cache/var/lib/apt:/var/lib/apt,builder/cache/var/cache/apt:/var/cache/apt,.:/pkg ' \
            '--pwd /pkg ' \
            '--fakeroot ' \
            '--cleanenv ' \
            '--containall ' \
            '--writable ' \
            '--no-home ' \
            '{img} {cmd}'

        # this is a fresh addition of the build env
        yield from builder_ds.containers_add(
            buildenv_name,
            image=str(buildenv),
            call_fmt=buildenv_callfmt,
            # tolerate an already existing record
            update=True,
            result_renderer='disabled',
            return_type='generator',
            # give control flow to caller
            on_failure='ignore',
        )

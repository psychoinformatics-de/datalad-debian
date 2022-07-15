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

    This command bootstraps a (containerized) build environment (such as a
    Singularity container) based on an existing builder configuration (such as
    a Singularity recipe).

    The execution of this command might require administrative privileges and
    could prompt for a sudo password, for example to build a
    Singularity image. The resulting bootstrapped build environment will be
    placed inside of a 'envs/' subdirectory of a 'builder/' dataset.

    The following directory tree illustrates this.
    The configured builder takes the form of a Singularity recipe here.

        |    bullseye                <- distribution dataset
        |    ├── builder             <- builder subdataset
        |    │   ├── envs
        |    │   │   ├── README.md
        |    │   │   └── singularity-amd64.sif   <- bootstrapped build environment
        |    │   └── recipes
        |    │       ├── README.md
        |    │       └── singularity-any     <- builder configuration

    """

    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a builder dataset that contains a build environment
            configuration""",
            constraints=EnsureDataset() | EnsureNone()),
    )

    _examples_ = [
        dict(text="Bootstrap a configured build environment in a builder "
                  "subdataset, from a distribution dataset",
             code_cmd="datalad deb-bootstrap-builder -d builder",
             code_py="deb_bootstrap_builder(dataset='builder')")
    ]

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
            "sudo singularity build --force {outputs} {inputs}",
            inputs=[str(recipe.relative_to(builder_ds.pathobj))],
            outputs=[str(buildenv)],
            message=f"Bootstrap builder '{buildenv_name}'",
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
            '--workdir {{tmpdir}} ' \
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

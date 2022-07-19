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
    EnsureChoice,
    EnsureNone,
    EnsureStr,
)
from datalad.support.param import Parameter

lgr = logging.getLogger('datalad.debian.bootstrap_builder')


@build_doc
class BootstrapBuilder(Interface):
    """Bootstrap a build environment

    This command bootstraps a (containerized) build environment (such as a
    Singularity container) based on an existing builder configuration (such as
    a Singularity recipe).
    If there are multiple builder configurations, the command will by default
    look for and bootstrap 'singularity-default-any' and
    'singularity-default-<arch-of-the-system>'. Alternative configurations
    can be specified using the cfgtype and template parameters, which will be
    combined into '{cfgtype}-{template}-<arch-of-the-system>'.

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
        |    │   │   └── singularity-default-amd64.sif   <- bootstrapped build environment
        |    │   └── recipes
        |    │       ├── README.md
        |    │       └── singularity-default-any     <- builder configuration

    """

    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a builder dataset that contains a build environment
            configuration""",
            constraints=EnsureDataset() | EnsureNone()),
        template=Parameter(
            args=('--template',),
            metavar='PATH',
            doc="""Template name of the relevant build environment. This value
            will be used to find the right build environment for the package in
            conjunction with cfgtype and the system's architecture""",
            constraints=EnsureStr() | EnsureNone()),
        cfgtype=Parameter(
            args=('--cfgtype',),
            default='singularity',
            doc="""Type of relevant build environment. This value will be used
            to find the right build environment for the package in conjunction
            with template and the system's architecture. Currently supported:
            'singularity'""",
            constraints=EnsureChoice('singularity')),
    )

    _examples_ = [
        dict(text="Bootstrap a configured build environment in a builder "
                  "subdataset, from a distribution dataset",
             code_cmd="datalad deb-bootstrap-builder -d builder",
             code_py="deb_bootstrap_builder(dataset='builder')"),
        dict(text="Bootstrap a configured nonfree build environment in a "
                  "builder subdataset, from a distribution dataset",
             code_cmd="datalad deb-bootstrap-builder --template nonfree "
                      "-d builder",
             code_py="deb_bootstrap_builder(dataset='builder', "
                     "template='nonfree')")
    ]

    @staticmethod
    @datasetmethod(name='deb_bootstrap_builder')
    @eval_results
    def __call__(*, dataset=None, cfgtype='singularity', template='default'):

        builder_ds = require_dataset(dataset)

        # figure out which architecture we will be building for
        binarch = Runner().run(
            ['dpkg-architecture', '-q', 'DEB_BUILD_ARCH'],
            protocol=StdOutCapture)['stdout'].strip()

        buildenv_name = f"{cfgtype}-{template}-{binarch}"

        recipe = None
        for p in (builder_ds.pathobj / 'recipes' / f"{cfgtype}-{template}-{binarch}",
                  builder_ds.pathobj / 'recipes' / f"{cfgtype}-{template}-any"):
            if p.exists():
                recipe = p
                break
        if recipe is None:
            raise RuntimeError(
                "Cannot locate build environment recipe for "
                f"{cfgtype}-{template}({binarch})")
        # define extensions of environment names and to-be-executed bootstrap
        # command based on specified cfgtype
        if cfgtype == 'singularity':
            ext = 'sif'
            # TODO allow for other means of privilege escalation
            cmd = 'sudo singularity build --force {outputs} {inputs}'
        # TODO allow for other types of environments
        else:
            raise NotImplementedError("No known extension and bootstrapping"
                                      "command for configuration of type %s"
                                      % cfgtype)
        buildenv = Path('envs', f"{buildenv_name}.{ext}")

        yield from builder_ds.run(
            cmd,
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

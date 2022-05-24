import json
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
from datalad.support.param import Parameter

lgr = logging.getLogger('datalad.debian.configure_builder')


@build_doc
class ConfigureBuilder(Interface):
    """Create a new package dataset
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a distribution dataset to add the package to""",
            constraints=EnsureDataset() | EnsureNone()),
        force=Parameter(
            args=("-f", "--force",),
            doc="""enforce creation of a package dataset in a
            non-empty directory""",
            action='store_true'),
        template=Parameter(
            args=('--template',),
            metavar='PATH',
            doc="""Builder recipe template. This is a text file for placeholders
            in Python string formating syntax""",
            constraints=EnsureStr() | EnsureNone()),
        spec=Parameter(
            args=('spec',),
            metavar='property=value',
            nargs='*',
            doc="""Stuff to complete the template"""),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_configure_builder')
    @eval_results
    def __call__(*, dataset=None, force=False,
                 template='default', spec=None,
    ):
        # TODO this could later by promoted to an option to support more than
        # singularity
        cfgtype = 'singularity'

        # TODO could later be promoted to an option to support
        # CPU architecture-specific configuration
        cfgarch = 'any'

        builder_ds = require_dataset(dataset)

        # TODO check if this is an actual builder dataset,
        # and give advice if not
        spec = normalize_specs(spec)

        tmpl_path = None
        for tp in (
                Path(template),
                Path(__file__).parent / 'resources' / 'recipes' / \
                f"{cfgtype}-{template}",
        ):
            if tp.exists():
                tmpl_path = tp
                break

        if tmpl_path is None:
            raise ValueError(
                f'Cannot locate builder configuration template {template!r}')

        template = tmpl_path.read_text()

        try:
            builder_config = template.format(**spec)
        except KeyError as e:
            raise ValueError(
                "Missing value for builder configuration template "
                f"instantiation: {e}"
            ) from e

        cfg_path = builder_ds.pathobj / 'recipes' / f'{cfgtype}-{cfgarch}'
        cfg_path.write_text(builder_config)
        yield from builder_ds.save(
            cfg_path,
            message='Set builder configuration',
            # do not use to_git=True, but honor the dataset config
            result_renderer='disabled',
            return_type='generator',
            on_failure='ignore',
        )


# Taken from datalad_next/credentials.py and simplified.
# TODO Could be RF'ed to a common base
def normalize_specs(specs):
    """Normalize all supported `spec` argument values

    Parameter
    ---------
    specs: JSON-formatted str or list

    Returns
    -------
    dict
        Keys are the names of any template placeholder and values are their
        replacements

    Raises
    ------
    ValueError
      For missing values, and invalid JSON input
    """
    if not specs:
        return {}
    elif isinstance(specs, str):
        try:
            specs = json.loads(specs)
        except json.JSONDecodeError as e:
            raise ValueError('Invalid JSON input') from e
    if isinstance(specs, list):
        # convert property assignment list
        specs = [
            (str(s[0]), str(s[1]))
            if isinstance(s, tuple) else
            (str(s),)
            if '=' not in s else
            (tuple(s.split('=', 1)))
            for s in specs
        ]
    if isinstance(specs, list):
        missing = [i[0] for i in specs if len(i) == 1]
    if missing:
        raise ValueError(
            f'Missing value(s) for property {missing!r}')
    if isinstance(specs, list):
        # expand absent values in tuples to ease conversion to dict below
        specs = [(i[0], i[1] if len(i) > 1 else None) for i in specs]
    specs = {
        k: v
        for k, v in (specs.items() if isinstance(specs, dict) else specs)
    }
    return specs



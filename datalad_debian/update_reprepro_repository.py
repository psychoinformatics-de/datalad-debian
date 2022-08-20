import logging
from pathlib import Path
from debian.deb822 import (
    Changes,
    Dsc,
)

from datalad.distribution.dataset import (
    EnsureDataset,
    datasetmethod,
    require_dataset,
)
from datalad.interface.base import (
    Interface,
    build_doc,
)
from datalad.interface.results import get_status_dict
from datalad.interface.utils import (
    eval_results,
)
from datalad.support.constraints import (
    EnsureNone,
    EnsureStr,
)
from datalad.support.param import Parameter


lgr = logging.getLogger('datalad.debian.new_distribution')


ckwa = dict(
    result_xfm=None,
    result_renderer='disabled',
    return_type='generator',
    # we leave the flow-control to the caller
    on_failure='ignore',
)


@build_doc
class UpdateRepreproRepository(Interface):
    """Update a (reprepro) Debian archive repository dataset
    """
    _params_ = dict(
        dataset=Parameter(
            args=("-d", "--dataset"),
            doc="""specify a dataset to update""",
            constraints=EnsureDataset() | EnsureNone()),
        path=Parameter(
            args=("path",),
            nargs='?',
            metavar='PATH',
            doc="""path to constrain the update to""",
            # put dataset 2nd to avoid useless conversion
            constraints=EnsureStr() | EnsureDataset() | EnsureNone()),
    )

    _examples_ = []

    @staticmethod
    @datasetmethod(name='deb_update_reprepro_repository')
    @eval_results
    def __call__(path=None, *, dataset=None):
        reprepro_ds = require_dataset(dataset)

        # TODO allow user-provided reference commitish
        # last recorded update of www subdataset
        last_update_hexsha = reprepro_ds.repo.call_git_oneline(
            ['log', '-1', '--format=%H'], files='www')
        lgr.debug('Using archive update ref %r', last_update_hexsha)

        # we want to make sure all the distributions are up-to-date,
        # we need the respective superdatasets to be able to run
        # update() on them
        yield from reprepro_ds.get(
            'distributions',
            get_data=False,
            recursive=True,
            recursion_limit=1,
            result_renderer="disabled",
        )

        dist_subdatasets = reprepro_ds.subdatasets(
            'distributions',
            result_xfm='datasets',
            result_renderer="disabled",
        )
        for dist_sds in dist_subdatasets:
            yield from dist_sds.update(
                # 'reset' means we intentionally discard any local change
                how='reset',
                follow='parentds-lazy',
                # we cannot limit recursion without risking a dataset hierarchy
                # that is not in-sync
                recursive=True,
                result_renderer="disabled",
            )
        yield from reprepro_ds.save(
            'distributions',
            message='Update distribution subdatasets',
            result_renderer="disabled",

        )

        # which distributions saw an update since the last update of 'www'
        # this is not necessarily identical to what was saved above
        updated_dists = [
            d for d in reprepro_ds.diff(
                'distributions',
                fr=last_update_hexsha,
                result_xfm='datasets',
                result_renderer='disabled')
            if d in dist_subdatasets
        ]
        # TODO could be done in parallel
        for ud in updated_dists:
            yield from _get_updates_from_dist(
                reprepro_ds,
                ud,
                last_update_hexsha,
            )


def _get_updates_from_dist(ds, dist_ds, ref):
    lgr.debug('Updating from %s', dist_ds.pathobj.relative_to(ds.pathobj))
    updated_pkg_datasets = [
        # we must use `ds` again to keep the validity of `ref`
        pkg_ds for pkg_ds in ds.diff(
            fr=ref,
            path=dist_ds.pathobj / 'packages',
            recursive=True,
            recursion_limit=1,
            result_xfm='datasets',
            result_renderer='disabled',
        )
        # we are not interested in the distribution dataset here
        if pkg_ds != dist_ds
    ]
    # TODO could be done in parallel
    for up in updated_pkg_datasets:
        yield from _get_updates_from_pkg(
            ds,
            # only use the part in front of the first '-'
            # as the target distribution label.
            # the full name could be different, when multiple
            # distribution packages (maybe with different builders)
            # are all targeting the same distribution in the archive
            dist_ds.pathobj.name.split('-', maxsplit=1)[0],
            up,
            ref,
        )


def _get_updates_from_pkg(ds, dist_codename, pkg_ds, ref):
    # TODO option to drop packages that were not present locally before?
    # make sure the package dataset is present locally
    lgr.debug('Updating from %s', pkg_ds.pathobj.relative_to(ds.pathobj))
    ds.get(
        path=pkg_ds.pathobj,
        get_data=False,
        result_renderer='disabled',
        return_type='item-or-list',
    )
    updated_files = [
        # we must use `ds` again to keep the validity of `ref`
        Path(r['path']) for r in ds.diff(
            fr=ref,
            path=pkg_ds.pathobj,
            recursive=True,
            recursion_limit=2,
            result_renderer='disabled',
        )
        # we can handle three types of files
        # - changes files from builds of any kind
        # - dsc of source packages
        # - lonely debs
        if r.get('state') in ('added', 'modified')
        and Path(r['path']).suffix in ('.changes', '.dsc', '.deb')
    ]
    if not updated_files:
        return
    # TODO option to give a single commit across all updates?
    # it won't have the prov-records from run, but it may be needed
    # for bring the amount of commits down to a sane level for
    # huge archives
    yield from _include_changes(ds, dist_codename, updated_files)
    if not updated_files:
        return
    yield from _include_dsc(ds, dist_codename, updated_files)
    if not updated_files:
        return
    yield from _include_deb(ds, dist_codename, updated_files)


def _include_changes(ds, dist_codename, updated_files):
    for changes in (c for c in updated_files if c.suffix == '.changes'):
        lgr.debug('Import CHANGES from %s', changes.relative_to(ds.pathobj))
        ds.get(
            path=changes,
            get_data=True,
            result_renderer='disabled',
        )
        # pull all files referenced by the CHANGES file from the list of
        # updated files, and do it now to avoid importing
        # pieces in case the dsc import fails for whatever reason
        changes_files = [
            changes.parent / f['name']
            for f in Changes(changes.read_text())['Files']
        ]
        changes_files.append(changes)
        for pull_file in changes_files:
            try:
                updated_files.remove(pull_file)
            except ValueError:
                # file not present, nothing to worry about
                pass
        yield from ds.run(
            # TODO should be forcibly take `dist_codename`, or forcibly
            # take changes['Distribution']?
            # The latter is sensible, but requires the package to be built
            # for a particular distribution (which means requiring a source
            # modification of debian/changelog to set the distribution,
            # even if a modification-less built would yield a working
            # package)
            # right now go with the more flexible "force dist_codename"
            # and guard against a mismatch
            f'reprepro --ignore=wrongdistribution include {dist_codename} {changes}',
            inputs=[str(p) for p in changes_files],
            result_renderer='disabled',
        )
        yield get_status_dict(
            status='ok',
            ds=ds,
            action='update_repository.includechanges',
            changes=str(changes),
        )


def _include_dsc(ds, dist_codename, updated_files):
    for dsc in (c for c in updated_files if c.suffix == '.dsc'):
        lgr.debug('Import DSC from %s', dsc.relative_to(ds.pathobj))
        ds.get(
            path=dsc,
            get_data=True,
            result_renderer='disabled',
        )
        # pull all files referenced by the DSC from the list of
        # updated files, and do it now to avoid importing
        # pieces in case the dsc import fails for whatever reason
        dsc_files = [
            dsc.parent / f['name']
            for f in Dsc((ds.pathobj / dsc).read_text())['Files']
        ]
        dsc_files.append(dsc)
        for pull_file in dsc_files:
            try:
                updated_files.remove(pull_file)
            except ValueError:
                # file not present, nothing to worry about
                pass
        # TODO add commit message
        yield from ds.run(
            f'reprepro includedsc {dist_codename} {dsc}',
            inputs=[str(p) for p in dsc_files],
            result_renderer='disabled',
        )
        yield get_status_dict(
            status='ok',
            ds=ds,
            action='update_repository.includedsc',
            dsc=str(dsc),
        )


def _include_deb(ds, dist_codename, updated_files):
    for deb in (c for c in updated_files if c.suffix == '.deb'):
        lgr.debug('Import DEB from %s', deb.relative_to(ds.pathobj))
        # TODO add commit message
        yield from ds.run(
            f'reprepro includedeb {dist_codename} {deb}',
            inputs=[str(deb)],
            result_renderer='disabled',
        )
        yield get_status_dict(
            status='ok',
            ds=ds,
            action='update_repository.includedeb',
            deb=str(deb),
        )

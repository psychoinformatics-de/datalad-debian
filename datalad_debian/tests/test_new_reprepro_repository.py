from pathlib import Path

from datalad.tests.utils_pytest import (
    assert_in_results,
    assert_repo_status,
    with_tempfile,
)

from datalad.api import (
    Dataset,
    deb_new_reprepro_repository,
    deb_add_distribution,
    deb_new_distribution,
)

ckwa = dict(result_renderer='disabled')


@with_tempfile
def test_new_reprepro_repository(path=None):
    pathobj = Path(path)
    res = deb_new_reprepro_repository(
        path=pathobj / 'archive',
        **ckwa)
    assert_in_results(
        res,
        path=str(pathobj / 'archive' / 'www'),
        type='dataset',
    )
    # Main README explains the layout & references datalad-debian
    assert (pathobj / 'archive' / 'README').exists()
    # README points out where distributions need to go
    assert (pathobj / 'archive' / 'distributions' / 'README').exists()
    # config placeholder for reprepro-recognized distributions is
    # placed in the dataset as an untracked file
    # the rest is clean
    assert_repo_status(
        pathobj / 'archive',
        untracked=[pathobj / 'archive' / 'conf' / 'distributions'])

    deb_new_distribution(pathobj / 'distribution', **ckwa)
    deb_add_distribution(
        # TODO the `clone` call inside cannot handle Path args
        str(pathobj / 'distribution'),
        'mydist',
        dataset=pathobj / 'archive',
        **ckwa
    )
    # check that the distribution dataset ends up in the right place with
    # the right name and version
    assert Dataset(pathobj / 'distribution').repo.get_hexsha() \
        == Dataset(pathobj / 'archive' / 'distributions' / 'mydist').repo.get_hexsha()

from pathlib import Path

from datalad.tests.utils_pytest import (
    assert_in_results,
    assert_repo_status,
    with_tempfile,
)

from datalad.api import deb_new_reprepro_repository

ckwa = dict(result_renderer='disabled')


@with_tempfile
def test_new_reprepro_repository(path=None):
    pathobj = Path(path)
    res = deb_new_reprepro_repository(
        path=path,
        **ckwa)
    assert_in_results(
        res,
        path=str(pathobj / 'www'),
        type='dataset',
    )
    # README points out where distributions need to go
    assert (pathobj / 'distributions' / 'README').exists()
    # config placeholder for reprepro-recognized distributions is
    # placed in the dataset as an untracked file
    # the rest is clean
    assert_repo_status(path, untracked=[pathobj / 'conf' / 'distributions'])

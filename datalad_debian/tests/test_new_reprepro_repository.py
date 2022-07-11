from pathlib import Path

from datalad.tests.utils_pytest import (
    assert_in_results,
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

from pathlib import Path
from datalad.tests.utils_pytest import (
    with_tempfile,
)
from datalad.api import (
    Dataset,
)


@with_tempfile
def test_from_scratch(wdir=None):
    da = {'result_renderer': 'disabled'}
    dist = Dataset(wdir)
    dist.deb_new_distribution(**da)
    dist.subdatasets(
        path='builder',
        set_property=[('url', str(Path(wdir) / 'builder'))])
    builder = Dataset(dist.pathobj / 'builder')
    builder.deb_configure_builder(spec={'dockerbase': 'debian:bullseye'})
    builder.deb_bootstrap_builder()
    dist.save(path='builder', message="Update distribution builder")
    dist.deb_new_package('hello')
    pkg_hello = Dataset(dist.pathobj / 'packages' / 'hello')
    pkg_hello.run(
        "dget -u -d http://deb.debian.org/debian/pool/main/h/hello/hello_2.10-2.dsc",
        message="Add version 2.10-2 source package")
    pkg_hello.deb_build_package('hello_2.10-2.dsc')
    dist.save(path='packages', message="Package update")

from pathlib import Path
from datalad.tests.utils_pytest import (
    assert_in_results,
    with_tempfile,
)
from datalad.api import (
    Dataset,
    deb_add_distribution,
    deb_new_reprepro_repository,
    deb_update_reprepro_repository,
    save,
)


@with_tempfile
def test_from_scratch(wdir=None):
    wdir = Path(wdir)
    da = {'result_renderer': 'disabled'}
    dist = Dataset(wdir / 'dist')
    dist.deb_new_distribution(**da)
    dist.subdatasets(
        path='builder',
        set_property=[('url', str(dist.pathobj / 'builder'))])
    builder = Dataset(dist.pathobj / 'builder')
    builder.deb_configure_builder(spec={'dockerbase': 'debian:bullseye-slim'})
    builder.deb_bootstrap_builder()
    dist.save(path='builder', message="Update distribution builder")
    dist.deb_new_package('hello')
    pkg_hello = Dataset(dist.pathobj / 'packages' / 'hello')
    pkg_hello.run(
        "dget -u -d http://deb.debian.org/debian/pool/main/h/hello/hello_2.10-2.dsc",
        message="Add version 2.10-2 source package")
    res = pkg_hello.deb_build_package('hello_2.10-2.dsc')
    dist.save(path='packages', message="Package update")
    # second part: take that distribution package and turn it into an APT archive
    archive_ds_p = wdir / 'archive'
    deb_new_reprepro_repository(archive_ds_p, **da)
    (archive_ds_p / 'conf' / 'distributions').write_text("""\
Codename: bullseye
Components: main
Architectures: source amd64
""")
    save(dataset=archive_ds_p, **da)
    deb_add_distribution(
        dataset=archive_ds_p,
        source=dist.path,
        name='bullseye',
        **da
    )
    res = deb_update_reprepro_repository(dataset=archive_ds_p, **da)
    # it processed the changes file
    assert_in_results(
        res,
        action='update_repository.includechanges',
        path=str(archive_ds_p),
        type='dataset',
        changes=str(
            archive_ds_p / 'distributions' / 'bullseye' / 'packages' /
            'hello' / 'hello_2.10-2_amd64.changes'),
    )
    # but also the associated DSC
    assert_in_results(
        res,
        action='update_repository.includedsc',
        path=str(archive_ds_p),
        type='dataset',
        dsc=str(
            archive_ds_p / 'distributions' / 'bullseye' / 'packages' /
            'hello' / 'hello_2.10-2.dsc'),
    )
    pooldir = archive_ds_p / 'www' / 'pool' / 'main' / 'h' / 'hello'
    # came via the DSC
    assert (pooldir / 'hello_2.10.orig.tar.gz').exists()
    # came via the CHANGES
    assert (pooldir / 'hello_2.10-2_amd64.deb').exists()

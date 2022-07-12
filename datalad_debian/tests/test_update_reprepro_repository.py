import gzip
from pathlib import Path

from datalad.tests.utils_pytest import (
    assert_in_results,
    assert_repo_status,
    with_tempfile,
)

from datalad.api import (
    Dataset,
    deb_add_distribution,
    deb_new_distribution,
    deb_new_package,
    deb_new_reprepro_repository,
    deb_update_reprepro_repository,
    run,
    save,
    update,
)

ckwa = dict(
    result_renderer='disabled',
)


@with_tempfile
def test_update_reprepro_repo(path=None):
    path = Path(path)
    dist_ds_p = path / 'dist'
    pkg_ds_p = path / 'dist' / 'packages' / 'tqdm'
    archive_ds_p = path / 'archive'
    # prepare a distribution, with a package
    deb_new_distribution(dist_ds_p, **ckwa)
    deb_new_package(dataset=dist_ds_p, name=pkg_ds_p.name, **ckwa)
    # download a tiny package
    # pull from snapshot.d.o for durability
    run('dget -u -d '
        'https://snapshot.debian.org/archive/debian/20210218T082603Z/pool/main/t/tqdm/tqdm_4.57.0-1.dsc',
        dataset=Dataset(pkg_ds_p),
        **ckwa
    )
    # package dataset is clean after run()
    assert_repo_status(pkg_ds_p)
    # make a clean distribution dataset too
    save(dataset=dist_ds_p, **ckwa)
    assert_repo_status(dist_ds_p)

    # now for the real thing. we are not going to build any package,
    # this will be a source-only distribution/archive (for reasons of
    # test-speed)
    deb_new_reprepro_repository(archive_ds_p, **ckwa)
    # write distribution config
    (archive_ds_p / 'conf' / 'distributions').write_text("""\
Codename: bullseye
Components: main
Architectures: source amd64
""")
    save(dataset=archive_ds_p, **ckwa)
    assert_repo_status(archive_ds_p)

    # register the distribution, up to this point we did not have to declare
    # any name
    deb_add_distribution(
        dataset=archive_ds_p,
        source=str(dist_ds_p),
        name='bullseye',
        **ckwa
    )
    deb_update_reprepro_repository(dataset=archive_ds_p, **ckwa)
    # we expect the orig.tar to be ingested into the pool/
    origtar = (archive_ds_p / 'www' / 'pool' / 'main' / 't' / 'tqdm' /
        'tqdm_4.57.0.orig.tar.xz')
    assert origtar.exists()
    # we expect the package to be listed in the source list
    assert b'tqdm_4.57.0-1' in gzip.open(
        archive_ds_p / 'www' / 'dists' / 'bullseye' / 'main' /
        'source' / 'Sources.gz').read()
    # update the test package, no orig.tar update
    run('dget -u -d '
        'https://snapshot.debian.org/archive/debian/20210305T143148Z/pool/main/t/tqdm/tqdm_4.57.0-2.dsc',
        dataset=Dataset(pkg_ds_p),
        **ckwa
    )
    # save the package update in the distribution package
    save(dataset=dist_ds_p, **ckwa)
    # update distribution packages within the archive dataset
    # TODO add option to do this automatically?
    # we must do unlimited recursive to catch any possibly present package
    # dataset too and maintain a consistent state of the entire hierarchy.
    # we use 'reset', because we want to pull from source whatever it has
    # and not support modifications done in the local clones
    update(dataset=archive_ds_p, how='reset', recursive=True, **ckwa)
    # now update the archive, it must replace -1 with -2
    res = deb_update_reprepro_repository(dataset=archive_ds_p, **ckwa)
    srcs = gzip.open(
        archive_ds_p / 'www' / 'dists' / 'bullseye' / 'main' /
        'source' / 'Sources.gz').read()
    assert b'tqdm_4.57.0-1' not in srcs
    assert b'tqdm_4.57.0-2' in srcs
    assert origtar.exists()
    assert_in_results(
        res,
        action='update_repository.includedsc',
        path=str(archive_ds_p),
        type='dataset',
        dsc=str(archive_ds_p / 'distributions' / 'bullseye' /
                'packages' / 'tqdm' / 'tqdm_4.57.0-2.dsc'),
    )
    # update again, this time only add a deb
    run('wget '
        'https://snapshot.debian.org/archive/debian/20220415T025620Z/pool/main/t/tqdm/python3-tqdm_4.64.0-1_all.deb',
        dataset=Dataset(pkg_ds_p),
        **ckwa
    )
    save(dataset=dist_ds_p, **ckwa)
    update(dataset=archive_ds_p, how='reset', recursive=True, **ckwa)
    res = deb_update_reprepro_repository(dataset=archive_ds_p, **ckwa)
    debinpool = (
        archive_ds_p / 'www' / 'pool' / 'main' / 't' / 'tqdm' /
        'python3-tqdm_4.64.0-1_all.deb')
    assert_in_results(
        res,
        action='update_repository.includedeb',
        path=str(archive_ds_p),
        type='dataset',
        deb=str(archive_ds_p / 'distributions' / 'bullseye' /
            'packages' / 'tqdm' / 'python3-tqdm_4.64.0-1_all.deb'),
    )
    assert debinpool.exists()
    assert '4.64.0-1' in (
        archive_ds_p / 'www' / 'dists' / 'bullseye' / 'main' / 'binary-amd64' /
        'Packages').read_text()

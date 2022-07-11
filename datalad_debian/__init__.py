"""DataLad Debian extension"""

__docformat__ = 'restructuredtext'

# defines a datalad command suite
# this symbold must be indentified as a setuptools entrypoint
# to be found by datalad
command_suite = (
    # description of the command suite, displayed in cmdline help
    "DataLad for working with Debian packages",
    [
        (
            'datalad_debian.new_distribution',
            'NewDistribution',
            'deb-new-distribution',
            'deb_new_distribution',
        ),
        (
            'datalad_debian.new_package',
            'NewPackage',
            'deb-new-package',
            'deb_new_package',
        ),
        (
            'datalad_debian.build_package',
            'BuildPackage',
            'deb-build-package',
            'deb_build_package',
        ),
        (
            'datalad_debian.configure_builder',
            'ConfigureBuilder',
            'deb-configure-builder',
            'deb_configure_builder',
        ),
        (
            'datalad_debian.bootstrap_builder',
            'BootstrapBuilder',
            'deb-bootstrap-builder',
            'deb_bootstrap_builder',
        ),
        (
            'datalad_debian.new_reprepro_repository',
            'NewRepreproRepository',
            'deb-new-reprepro-repository',
            'deb_new_reprepro_repository',
        ),
    ]
)

from datalad import setup_package
from datalad import teardown_package

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

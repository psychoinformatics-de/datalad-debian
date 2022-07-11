#!/usr/bin/env python

import sys
from setuptools import setup
import versioneer

from _datalad_buildsupport.setup import (
    BuildManPage,
)

cmdclass = versioneer.get_cmdclass()
cmdclass.update(build_manpage=BuildManPage)

if __name__ == '__main__':
    setup(
        name='datalad_debian',
        version=versioneer.get_version(),
        cmdclass=cmdclass,
        entry_points={
            'datalad.metadata.extractors': [
                'debian_package_dataset=datalad_debian.metadata.extractors.debian_package_dataset:DebianPackageExtractor',
            ]
        }
    )


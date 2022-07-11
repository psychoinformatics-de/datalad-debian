# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""MetadataRecord extractor for built debian packages"""
import logging
from dataclasses import dataclass
from typing import (
    List,
    Optional,
)
from uuid import UUID

from debian.deb822 import (
    BuildInfo,
    Changes,
    Dsc,
)
from debian.debfile import DebFile
from datalad.api import get
from datalad_metalad.extractors.base import (
    DatasetMetadataExtractor,
    DataOutputCategory,
    ExtractorResult,
)


@dataclass
class DebianPackageVersion:
    name: str
    upstream_version: str
    debian_revision: str
    platforms: List


lgr = logging.getLogger('datalad.debian.extractors.package')


class DebianPackageElementNames:
    def __init__(self,
                 name: str,
                 upstream_version: str,
                 debian_revision: str,
                 platform: Optional[str] = None):

        upstream_name = f"{name}_{upstream_version}"
        debian_name = f"{upstream_name}-{debian_revision}"
        platform_name = f"{debian_name}_{platform}"
        dbgsym_name = platform_name.replace(f"{name}_", f"{name}-dbgsym_")

        self._names = {
            "dsc": f"{debian_name}.dsc",
            "orig": f"{upstream_name}.orig.tar.gz",
            "debian": f"{debian_name}.debian.tar.gz",
            **({
                "deb": f"{platform_name}.deb",
                "dbgsym": f"{dbgsym_name}.deb",
                "changes": f"{platform_name}.changes",
                "buildinfo": f"{platform_name}.buildinfo",
            } if platform else {}),
        }

    def __getitem__(self, item):
        return self._names[item]

    def __len__(self):
        return len(self._names)

    def keys(self):
        return self._names.keys()

    def items(self):
        return self._names.items()

    def values(self):
        return self._names.values()


class DebianPackageExtractor(DatasetMetadataExtractor):

    def get_id(self) -> UUID:
        return UUID("d6203798-fa94-49d8-b71e-54d5fa63a7b4")

    def get_version(self) -> str:
        return "0.0.1"

    def get_data_output_category(self) -> DataOutputCategory:
        return DataOutputCategory.IMMEDIATE

    def get_required_content(self) -> bool:
        get(path=".", dataset=self.dataset)
        return True

    def extract(self, x=None) -> ExtractorResult:
        if 'package-name' not in self.parameter:
            return ExtractorResult(
                extractor_version=self.get_version(),
                extraction_parameter=self.parameter or {},
                extraction_success=False,
                datalad_result_dict={
                    "type": "dataset",
                    "status": "error",
                    "message": "missing parameter: 'package-name'"
                },
                immediate_data=None)

        d = self.dataset.pathobj
        for version_info in self._find_versions():
            source_element_name = DebianPackageElementNames(
                version_info.name,
                version_info.upstream_version,
                version_info.debian_revision)

            source_info = {
                "dsc": str(Dsc(open(d / source_element_name["dsc"], "rt"))),
                "orig": "NOT IMPLEMENTED",
                "debian": "NOT IMPLEMENTED",
            }

            binary_names = {
                platform: DebianPackageElementNames(
                    version_info.name,
                    version_info.upstream_version,
                    version_info.debian_revision,
                    platform)
                for platform in version_info.platforms

            }
            binary_infos = {
                platform: {
                    "deb": str(DebFile(d / binary_names[platform]["deb"])),
                    "dbgsym": str(DebFile(d / binary_names[platform]["dbgsym"])),
                    "build_info": str(BuildInfo(open(d / binary_names[platform]["buildinfo"], "rt"))),
                    "changes": str(Changes(open(d / binary_names[platform]["changes"], "rt")))
                }
                for platform in version_info.platforms
            }
            return ExtractorResult(
                extractor_version=self.get_version(),
                extraction_parameter=self.parameter or {},
                extraction_success=True,
                datalad_result_dict={
                    "type": "dataset",
                    "status": "ok",
                },
                immediate_data={
                    "source": source_info,
                    "binaries": binary_infos,
                })

    def _find_versions(self):
        """Find all versions and platforms

        Find all versions, i.e. upstream_version and debian_revision. Version
        detection is based on '.dsc'-files. Platforms are determined based on
        '.deb' files.
        """

        name = self.parameter["package-name"]
        package_dir = self.dataset.pathobj

        for path in package_dir.glob(f"{name}_*.dsc"):
            assert path.is_file() is True, f"Not a file: {path}"
            version_info = path.name[len(name) + 1:-4]
            if "-" in version_info:
                upstream_version, debian_revision = version_info.split("-")
            else:
                upstream_version, debian_revision = version_info, 0

            platform_paths = [
                platform_path.name[len(f"{name}_{version_info}_"):-4]
                for platform_path
                in package_dir.glob(f"{name}_{version_info}_*.deb")]

            yield DebianPackageVersion(
                name,
                upstream_version,
                debian_revision,
                platform_paths)

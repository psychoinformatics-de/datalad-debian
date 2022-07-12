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
    version_string: str
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
        debian_name = (
            f"{upstream_name}-{debian_revision}"
            if debian_revision != "0"
            else upstream_name
        )
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

    def extract(self, _=None) -> ExtractorResult:

        d = self.dataset.pathobj

        package_name = None
        upstream_versions = {}

        for version_info in self._find_versions():
            source_element_names = DebianPackageElementNames(
                version_info.name,
                version_info.upstream_version,
                version_info.debian_revision
            )

            package_name = version_info.name
            package_dsc = Dsc(open(d / source_element_names["dsc"], "rt"))
            source_info = {
                "dsc": str(package_dsc),
                "orig": "NOT IMPLEMENTED",
                "debian": "NOT IMPLEMENTED"
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
                platform: self._get_binary_info(d, binary_names[platform])
                for platform in version_info.platforms
            }

            if version_info.upstream_version not in upstream_versions:
                upstream_versions[version_info.upstream_version] = {
                    "orig": f"(NOT IMPLEMENTED): {source_element_names['orig']}",
                    "debian_revisions": {}
                }
            version_dict = upstream_versions[version_info.upstream_version]

            if version_info.debian_revision not in version_dict["debian_revisions"]:
                version_dict["debian_revisions"][version_info.debian_revision] = {
                    "binaries": {}
                }
            revision_dict = version_dict["debian_revisions"][version_info.debian_revision]

            revision_dict["debian"] = f"{source_element_names['debian']}"
            revision_dict["maintainer"] = f"{package_dsc['maintainer']}"
            revision_dict["homepage"] = f"{package_dsc['homepage']}"

            for platform, element_names in binary_names.items():
                assert platform not in revision_dict["binaries"]
                revision_dict["binaries"][platform] = binary_infos[platform]

        return ExtractorResult(
            extractor_version=self.get_version(),
            extraction_parameter=self.parameter or {},
            extraction_success=True,
            datalad_result_dict={
                "type": "dataset",
                "status": "ok",
            },
            immediate_data={
                "name": package_name,
                "upstream_version": upstream_versions,
            }
        )

    def _get_binary_info(self, path, names):
        return {
            "deb": f"{names['deb']} {DebFile(path / names['deb'])}",
            "dbgsym": f"{names['dbgsym']} {DebFile(path / names['dbgsym'])}",
            "build_info": f"{names['buildinfo']} {BuildInfo(open(path / names['buildinfo'], 'rt'))}",
            "changes": f"{names['changes']} {Changes(open(path / names['changes'], 'rt'))}",
        }

    def _find_versions(self):
        """Find all versions and platforms

        Find all versions, i.e. upstream_version and debian_revision. Version
        detection is based on '.dsc'-files. Platforms are determined based on
        '.deb' files.
        """
        package_dir = self.dataset.pathobj

        all_names = set()
        for path in package_dir.glob("*.dsc"):

            assert path.is_file() is True, f"Not a file: {path}"
            name = path.name.split('_')[0]
            all_names.add(name)
            assert len(all_names) == 1, f"More than one packet name found: {str(all_names)}"

            version_info = path.name[len(name) + 1:-4]
            if "-" in version_info:
                upstream_version, debian_revision = version_info.split("-")
            else:
                upstream_version, debian_revision = version_info, "0"

            dsc = Dsc(path.open("rt"))
            assert dsc["source"] == package_dir.name, f"directory name ({package_dir.name}) does not match source ({dsc['source']}) in .dsc-file."
            assert dsc["source"] == name, f"file name ({name}) does not match source ({dsc['source']}) in .dsc-file."
            assert dsc["version"] == version_info, f"version in file name ({version_info}) does not match version ({dsc['version']}) in .dsc-file."

            platform_paths = [
                platform_path.name[len(f"{name}_{version_info}_"):-4]
                for platform_path
                in package_dir.glob(f"{name}_{version_info}_*.deb")]

            yield DebianPackageVersion(
                name,
                version_info,
                upstream_version,
                debian_revision,
                platform_paths)

import codecs
import json
import pathlib
import tempfile
import warnings
from abc import abstractmethod
from typing import MutableSequence, Sequence

from packaging import version

from slicedimage.url.resolve import resolve_url
from ._keys import CommonPartitionKeys


_VERSIONS = []  # type: MutableSequence


class Reader:
    @staticmethod
    def parse_doc(name_or_url, baseurl, backend_config=None):
        backend, name, baseurl = resolve_url(name_or_url, baseurl, backend_config)
        with backend.read_contextmanager(name) as fh:
            reader = codecs.getreader("utf-8")
            json_doc = json.load(reader(fh))

        try:
            doc_version = version.parse(json_doc[CommonPartitionKeys.VERSION])
        except KeyError as ex:
            raise KeyError(
                "JSON document missing `version` field. "
                "Please specify the file format version.") from ex

        try:
            for version_cls in VERSIONS:
                if version_cls.Reader.can_parse(doc_version):
                    parser = version_cls.Reader()
                    break
            else:
                raise ValueError("Unrecognized version number")
        except KeyError:
            raise KeyError(
                "JSON document missing `version` field. Please specify the file format version.")

        return parser.parse(json_doc, baseurl, backend_config)

    @classmethod
    @abstractmethod
    def can_parse(cls, doc_version: version.Version):
        raise NotImplementedError()

    @abstractmethod
    def parse(self, json_doc, baseurl, backend_config):
        raise NotImplementedError()


class Writer:
    @staticmethod
    def write_to_path(partition, path, pretty=False, version_class=None, *args, **kwargs):
        if isinstance(path, str):
            warnings.warn("Paths should be passed in as pathlib.Path objects", DeprecationWarning)
            path = pathlib.Path(path)
        if version_class is None:
            version_class = VERSIONS[-1]
        document = version_class.Writer().generate_partition_document(
            partition, path, pretty, *args, **kwargs)
        indent = 4 if pretty else None
        with open(str(path), "w") as fh:
            json.dump(document, fh, indent=indent, sort_keys=pretty)

    @staticmethod
    def default_partition_path_generator(parent_partition_path, partition_name):
        parent_partition_stem = parent_partition_path.stem
        partition_file = tempfile.NamedTemporaryFile(
            suffix=".json",
            prefix="{}-".format(parent_partition_stem),
            dir=str(parent_partition_path.parent),
            delete=False,
        )
        return pathlib.Path(partition_file.name)

    @staticmethod
    def default_tile_opener(tileset_path, tile, ext):
        tileset_stem = tileset_path.stem
        return tempfile.NamedTemporaryFile(
            suffix=".{}".format(ext),
            prefix="{}-".format(tileset_stem),
            dir=str(tileset_path.parent),
            delete=False,
        )

    @abstractmethod
    def generate_partition_document(self, partition, path, pretty=False, *args, **kwargs):
        raise NotImplementedError()


def _parse_collection(parse_method, baseurl, backend_config):
    """Return a method that binds a parse method, a baseurl, and a backend config to a method that
    accepts name and path of a partition belonging to a collection.  The method should then return
    the name and the parsed partition data.
    """
    def parse(name_relative_path_or_url_tuple):
        name, relative_path_or_url = name_relative_path_or_url_tuple
        partition = parse_method(relative_path_or_url, baseurl, backend_config)
        partition._name_or_url = relative_path_or_url

        return name, partition

    return parse


# this has to be at the end of this file to prevent recursive imports.
from ._v0_0_0 import v0_0_0  # noqa
from ._v0_1_0 import v0_1_0  # noqa
_VERSIONS.append(v0_0_0)
_VERSIONS.append(v0_1_0)

VERSIONS = tuple(_VERSIONS)  # type: Sequence
"""All the different versions of the file format, in order from oldest to newest."""

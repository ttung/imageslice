import codecs
import json
import hashlib
import urllib.parse
import warnings
from abc import abstractmethod
from io import BytesIO
from pathlib import Path, PurePath, PurePosixPath
from typing import (
    BinaryIO,
    Callable,
    cast,
    Mapping,
    MutableSequence,
    Optional,
    Sequence,
    TextIO,
    Union,
)

from packaging import version

from slicedimage.url.resolve import resolve_url
from slicedimage._collection import Collection
from slicedimage._formats import ImageFormat
from slicedimage._tile import Tile
from slicedimage._tileset import TileSet
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
    def write_to_path(
            partition: Union[Collection, TileSet],
            path: Path,
            pretty: bool = False,
            version_class=None,
            *args, **kwargs):
        if isinstance(path, str):
            warnings.warn("Paths should be passed in as pathlib.Path objects", DeprecationWarning)
            path = Path(path)
        if not path.is_absolute():
            path = path.absolute()
        if version_class is None:
            version_class = VERSIONS[-1]

        partition_path_generator = None  # type: Optional[Callable[[PurePath, str], Path]]
        if len(args) > 0:
            partition_path_generator = args[0]
            args = args[1:]
        elif 'partition_path_generator' in kwargs:
            partition_path_generator = kwargs.pop('partition_path_generator')
        if partition_path_generator is not None:
            warnings.warn(
                "`partition_path_generator` is deprecated.  Please use `WriterContract` to control "
                "the behavior of image writing",
                DeprecationWarning
            )

        tile_opener = None  # type: Optional[Callable[[PurePath, Tile, str], BinaryIO]]
        if len(args) > 0:
            tile_opener = args[0]
            args = args[1:]
        elif 'tile_opener' in kwargs:
            tile_opener = kwargs.pop('tile_opener')
        if tile_opener is not None:
            warnings.warn(
                "`tile_opener` is deprecated.  Please use `WriterContract` to control the behavior "
                "of image writing",
                DeprecationWarning
            )

        writer_contract = None  # type: Optional[WriterContract]
        if len(args) > 0:
            writer_contract = args[0]
            args = args[1:]
        elif 'writer_contract' in kwargs:
            writer_contract = kwargs.pop('writer_contract')

        if partition_path_generator is not None or tile_opener is not None:
            if writer_contract is not None:
                raise ValueError(
                    "Cannot specify both `writer_contract` and `partition_path_generator` or "
                    "`tile_opener`")
            kwargs['writer_contract'] = CompatibilityWriterContract(
                partition_path_generator, tile_opener)
        elif writer_contract is not None:
            kwargs['writer_contract'] = writer_contract
        else:
            kwargs['writer_contract'] = WriterContract()

        return Writer.write_to_url(partition, path.as_uri(), pretty, version_class, *args, **kwargs)

    @staticmethod
    def write_to_url(
            partition: Union[Collection, TileSet],
            url: str,
            pretty: bool = False,
            version_class=None,
            *args, **kwargs):
        if version_class is None:
            version_class = VERSIONS[-1]

        document = version_class.Writer().generate_partition_document(
            partition, url, pretty, *args, **kwargs)
        indent = 4 if pretty else None

        backend, name, _ = resolve_url(url)
        with backend.write_file_handle(name) as fh:
            writer = cast(TextIO, codecs.getwriter("utf-8")(fh))
            json.dump(document, writer, indent=indent, sort_keys=pretty, ensure_ascii=False)

    @abstractmethod
    def generate_partition_document(
            self,
            partition: Union[Collection, TileSet],
            url: str,
            pretty: bool = False,
            *args, **kwargs):
        raise NotImplementedError()


class WriterContract(object):
    def partition_url_generator(self, parent_partition_url: str, partition_name: str) -> str:
        """Given the url of the parent partition and the name of a partition to be added to the
        parent partition, return the url of the resulting of the resulting partition.

        Parameters
        ----------
        parent_partition_url : str
            The URL of the parent partition.
        partition_name : str
            The name of the partition we're adding to the parent partition.

        Returns
        -------
        str :
            The URL of the partition being added.
        """
        parent_parsed_url = urllib.parse.urlparse(parent_partition_url)
        parent_path = PurePosixPath(parent_parsed_url.path)
        parent_stem = parent_path.stem
        partition_path = parent_path.parent / "{}-{}.json".format(parent_stem, partition_name)
        partition_parsed_url = parent_parsed_url._replace(path=str(partition_path))
        return urllib.parse.urlunparse(partition_parsed_url)

    def tile_url_generator(self, tileset_url: str, tile: Tile, ext: str) -> str:
        """Given the url of a tileset and a tile to be added to the tileset, return the url where
        the tile data is written to.

        Parameters
        ----------
        tileset_url : str
            The URL of the tileset
        tile : Tile
            The tile to be added to the tileset.
        ext : str
            The extension to be used for writing the tile data.

        Returns
        -------
        str :
            The URL of the tile being added.
        """
        tileset_parsed_url = urllib.parse.urlparse(tileset_url)
        tileset_path = PurePosixPath(tileset_parsed_url.path)
        tileset_stem = tileset_path.stem
        indices_sorted_str = "-".join([
            "{}{}".format(index_name, tile.indices[index_name])
            for index_name in sorted(tile.indices.keys())
        ])
        tile_path = tileset_path.parent / "{}-{}.{}".format(tileset_stem, indices_sorted_str, ext)
        tile_parsed_url = tileset_parsed_url._replace(path=str(tile_path))
        return urllib.parse.urlunparse(tile_parsed_url)

    def write_tile(
            self,
            tile_url: str,
            tile: Tile,
            tile_format: ImageFormat,
            backend_config: Optional[Mapping] = None,
    ) -> str:
        """Write the data for a tile to a given URL.

        Parameters
        ----------
        tile_url : str
            The URL of the tile.
        tile : Tile
            The tile to be written.
        tile_format : ImageFormat
            The format to write the tile in.
        backend_config : Optional[Mapping]
            Mapping from the backend names to the config

        Returns
        -------
        str :
            The sha256 of the tile being added.
        """
        backend, name, _ = resolve_url(tile_url, backend_config=backend_config)
        buffer_fh = BytesIO()
        tile.write(buffer_fh, tile_format)

        buffer_fh.seek(0)
        sha256 = hashlib.sha256(buffer_fh.getvalue()).hexdigest()

        buffer_fh.seek(0)
        with backend.write_file_handle(name) as fh:
            fh.write(buffer_fh.read())

        return sha256


class CompatibilityWriterContract(WriterContract):
    """This provides a WriterContract to support the previous API of partition_path_generator and
    tile_opener.  This compatibility layer only works with URLs with the scheme ``file``."""
    def __init__(
            self,
            partition_path_generator: Optional[Callable[[PurePath, str], Path]] = None,
            tile_opener: Optional[Callable[[PurePath, Tile, str], BinaryIO]] = None,
    ):
        self.partition_path_generator = partition_path_generator
        self.tile_opener = tile_opener

    def partition_url_generator(self, parent_partition_url: str, partition_name: str) -> str:
        """Given the url of the parent partition and the name of a partition to be added to the
        parent partition, return the url of the resulting of the resulting partition.

        Parameters
        ----------
        parent_partition_url : str
            The URL of the parent partition.
        partition_name : str
            The name of the partition we're adding to the parent partition.

        Returns
        -------
        str :
            The URL of the partition being added.
        """
        if self.partition_path_generator is None:
            return super().partition_url_generator(parent_partition_url, partition_name)
        parent_parsed_url = urllib.parse.urlparse(parent_partition_url)
        assert parent_parsed_url.scheme == "file"
        parent_path = PurePosixPath(parent_parsed_url.path)
        partition_path = self.partition_path_generator(parent_path, partition_name)
        partition_parsed_url = parent_parsed_url._replace(path=str(partition_path))
        return urllib.parse.urlunparse(partition_parsed_url)

    def tile_url_generator(self, tileset_url: str, tile: Tile, ext: str) -> str:
        """Given the url of a tileset and a tile to be added to the tileset, return the url where
        the tile data is written to.

        Parameters
        ----------
        tileset_url : str
            The URL of the tileset
        tile : Tile
            The tile to be added to the tileset.
        ext : str
            The extension to be used for writing the tile data.

        Returns
        -------
        str :
            The URL of the tile being added.
        """
        if self.tile_opener is None:
            return super().tile_url_generator(tileset_url, tile, ext)
        tileset_parsed_url = urllib.parse.urlparse(tileset_url)
        assert tileset_parsed_url.scheme == "file"
        tileset_path = PurePosixPath(tileset_parsed_url.path)
        with self.tile_opener(tileset_path, tile, ext) as open_fh:
            tile_path = open_fh.name

        tile_parsed_url = tileset_parsed_url._replace(path=str(tile_path))
        return urllib.parse.urlunparse(tile_parsed_url)


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

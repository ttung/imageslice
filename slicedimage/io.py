import codecs
import hashlib
import json
import os
import tempfile
import urllib.parse
import warnings
from io import BytesIO
from multiprocessing.pool import ThreadPool

import pathlib
from packaging import version

from .backends import CachingBackend, DiskBackend, HttpBackend, S3Backend, SIZE_LIMIT
from .urlpath import pathjoin, pathsplit
from ._collection import Collection
from ._compat import fspath
from ._formats import ImageFormat
from ._tile import Tile
from ._tileset import TileSet
from ._typeformatting import format_enum_keyed_dicts


def infer_backend(baseurl, backend_config=None):
    """
    Guess the backend based on the format of `baseurl`, the consistent part of the URL or file path.
    The backend_config dictionary can contain flexible parameters for the different backends.

    Caching parameter keys include:

     - ["caching"]["directory"]  (default: None which disables caching)
     - ["caching"]["debug"]      (default: False)
     - ["caching"]["size_limit"] (default: SIZE_LIMIT)

    """
    if backend_config is None:
        backend_config = {}

    parsed = urllib.parse.urlparse(baseurl)

    if parsed.scheme == "file":
        posix_path = pathlib.PurePosixPath(parsed.path)
        local_path = pathlib.Path(*posix_path.parts)
        return DiskBackend(fspath(local_path))

    if parsed.scheme in ("http", "https"):
        backend = HttpBackend(baseurl)
    elif parsed.scheme == "s3":
        s3_config = backend_config.get("s3", {})
        backend = S3Backend(baseurl, s3_config)
    else:
        raise ValueError(
            "Unable to infer backend for url {}, please verify that baseurl points to a valid "
            "directory or web address".format(baseurl))

    # these backends might use a cache.
    cache_config = backend_config.get("caching", {})

    cache_dir = cache_config.get("directory", None)
    if cache_dir is not None:
        cache_dir = os.path.expanduser(cache_dir)
        size_limit = cache_config.get("size_limit", SIZE_LIMIT)
        if size_limit > 0:
            debug = cache_config.get("debug", False)
            if debug:
                print("> caching {} to {} (size_limit: {})".format(
                    baseurl, cache_dir, size_limit))
            backend = CachingBackend(cache_dir, backend, size_limit)

    return backend


def resolve_path_or_url(path_or_url, backend_config=None):
    """
    Given either a path (absolute or relative), or a URL, attempt to resolve it.  Returns a tuple
    consisting of: a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and
    the baseurl of the object.
    """
    try:
        return resolve_url(path_or_url, backend_config=None)
    except ValueError:
        if os.path.isfile(path_or_url):
            # convert this to a posix path
            native_path = pathlib.Path(path_or_url)
            return resolve_url(
                native_path.name,
                baseurl=native_path.parent.absolute().as_uri(),
                backend_config=backend_config
            )
        raise


def _resolve_absolute_url(absolute_url, backend_config):
    """
    Given a string that is an absolute URL, return a tuple consisting of: a
    :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of
    the object.
    """
    splitted = pathsplit(absolute_url)
    backend = infer_backend(splitted[0], backend_config)
    return backend, splitted[1], splitted[0]


def resolve_url(name_or_url, baseurl=None, backend_config=None):
    """
    Given a string that can either be a name or a fully qualified url, return a tuple consisting of:
    a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of
    the object.

    If the string is a name and not a fully qualified url, then baseurl must be set.  If the string
    is a fully qualified url, then baseurl is ignored.
    """
    try:
        # assume it's a fully qualified url.
        return _resolve_absolute_url(name_or_url, backend_config)
    except ValueError:
        if baseurl is None:
            # oh, we have no baseurl.  punt.
            raise
        absolute_url = pathjoin(baseurl, name_or_url)
        return _resolve_absolute_url(absolute_url, backend_config)


class Reader:
    @staticmethod
    def parse_doc(name_or_url, baseurl, backend_config=None):
        backend, name, baseurl = resolve_url(name_or_url, baseurl, backend_config)
        with backend.read_contextmanager(name) as fh:
            reader = codecs.getreader("utf-8")
            json_doc = json.load(reader(fh))
        doc_version = version.parse(json_doc[CommonPartitionKeys.VERSION])

        try:
            if doc_version >= version.parse(v0_1_0.VERSION):
                parser = v0_1_0.Reader()
            elif doc_version >= version.parse(v0_0_0.VERSION):
                parser = v0_0_0.Reader()
            else:
                raise ValueError("Unrecognized version number")
        except KeyError:
            raise KeyError(
                "JSON document missing `version` field. Please specify the file format version.")

        return parser.parse(json_doc, baseurl, backend_config)

    def parse(self, json_doc, baseurl, backend_config):
        raise NotImplementedError()


class Writer:
    @staticmethod
    def write_to_path(partition, path, pretty=False, version_class=None, *args, **kwargs):
        if isinstance(path, str):
            warnings.warn("Paths should be passed in as pathlib.Path objects", DeprecationWarning)
            path = pathlib.Path(path)
        if version_class is None:
            version_class = v0_1_0
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


class v0_0_0:
    VERSION = "0.0.0"

    class Reader(Reader):
        def parse(self, json_doc, baseurl, backend_config):
            if CollectionKeys.CONTENTS in json_doc:
                # this is a Collection
                result = Collection(json_doc.get(CommonPartitionKeys.EXTRAS, None))
                tp = ThreadPool()
                try:
                    func = _parse_collection(Reader.parse_doc, baseurl, backend_config)
                    results = tp.map(func, json_doc[CollectionKeys.CONTENTS].items())
                finally:
                    tp.terminate()
                for name, partition in results:
                    result.add_partition(name, partition)
            elif TileSetKeys.TILES in json_doc:
                imageformat = json_doc.get(TileSetKeys.DEFAULT_TILE_FORMAT, None)
                if imageformat is not None:
                    imageformat = ImageFormat[imageformat]

                result = TileSet(
                    tuple(json_doc[TileSetKeys.DIMENSIONS]),
                    json_doc[TileSetKeys.SHAPE],
                    Tile.format_tuple_shape_to_dict_shape(
                        json_doc.get(TileSetKeys.DEFAULT_TILE_SHAPE, None)),
                    imageformat,
                    json_doc.get(TileSetKeys.EXTRAS, None),
                )

                for tile_doc in json_doc[TileSetKeys.TILES]:
                    relative_path_or_url = tile_doc[TileKeys.FILE]
                    backend, name, _ = resolve_url(relative_path_or_url, baseurl, backend_config)

                    tile_format_str = tile_doc.get(TileKeys.TILE_FORMAT, None)
                    if tile_format_str:
                        tile_format = ImageFormat[tile_format_str]
                    else:
                        tile_format = result.default_tile_format
                    if tile_format is None:
                        # Still none :(
                        extension = os.path.splitext(name)[1].lstrip(".")
                        tile_format = ImageFormat.find_by_extension(extension)
                    checksum = tile_doc.get(TileKeys.SHA256, None)
                    tile = Tile(
                        tile_doc[TileKeys.COORDINATES],
                        tile_doc[TileKeys.INDICES],
                        tile_shape=Tile.format_tuple_shape_to_dict_shape(
                            tile_doc.get(TileKeys.TILE_SHAPE, None)),
                        sha256=checksum,
                        extras=tile_doc.get(TileKeys.EXTRAS, None),
                    )

                    def future_maker(_source_fh_contextmanager, _tile_format):
                        """Produces a future that reads from a file and decodes according to the
                        specified file format."""
                        def _actual_future():
                            with _source_fh_contextmanager as fh:
                                return _tile_format.reader_func(fh)

                        return _actual_future

                    tile.set_numpy_array_future(
                        future_maker(
                            backend.read_contextmanager(name, checksum_sha256=checksum),
                            tile_format))
                    result.add_tile(tile)
            else:
                raise ValueError(
                    "JSON doc does not appear to be a collection partition or a tileset "
                    "partition. JSON doc must contain either a {contents} field pointing to a "
                    "tile manifest, or it must contain a {tiles} field that specifies a set of "
                    "tiles.".format(
                        contents=CollectionKeys.CONTENTS, tiles=TileSetKeys.TILES))

            return result

    class Writer(Writer):
        def generate_partition_document(
                self,
                partition,
                path,
                pretty=False,
                partition_path_generator=Writer.default_partition_path_generator,
                tile_opener=Writer.default_tile_opener,
                tile_format=ImageFormat.NUMPY,
        ):
            if isinstance(path, str):
                warnings.warn("Paths should be passed in as pathlib.Path objects",
                              DeprecationWarning)
                path = pathlib.Path(path)

            json_doc = {
                CommonPartitionKeys.VERSION: v0_0_0.VERSION,
                CommonPartitionKeys.EXTRAS: partition.extras,
            }
            if isinstance(partition, Collection):
                json_doc[CollectionKeys.CONTENTS] = dict()
                for partition_name, partition in partition._partitions.items():
                    partition_path = partition_path_generator(path, partition_name)
                    Writer.write_to_path(
                        partition, partition_path, pretty,
                        version_class=v0_0_0,
                        partition_path_generator=partition_path_generator,
                        tile_opener=tile_opener,
                        tile_format=tile_format,
                    )
                    json_doc[CollectionKeys.CONTENTS][partition_name] = str(
                        partition_path.relative_to(path.parent))
                return json_doc
            elif isinstance(partition, TileSet):
                json_doc[TileSetKeys.DIMENSIONS] = tuple(partition.dimensions)
                json_doc[TileSetKeys.SHAPE] = partition.shape
                json_doc[TileSetKeys.TILES] = []

                if partition.default_tile_shape is not None:
                    json_doc[TileSetKeys.DEFAULT_TILE_SHAPE] = \
                        Tile.format_dict_shape_to_tuple_shape(partition.default_tile_shape)
                if partition.default_tile_format is not None:
                    json_doc[TileSetKeys.DEFAULT_TILE_FORMAT] = partition.default_tile_format.name
                if len(partition.extras) != 0:
                    json_doc[TileSetKeys.EXTRAS] = partition.extras

                for tile in partition._tiles:
                    tiledoc = {
                        TileKeys.COORDINATES: tile.coordinates,
                        TileKeys.INDICES: tile.indices,
                    }

                    with tile_opener(path, tile, tile_format.file_ext) as tile_fh:
                        buffer_fh = BytesIO()
                        tile.write(buffer_fh, tile_format)

                        buffer_fh.seek(0)
                        tile.sha256 = hashlib.sha256(buffer_fh.getvalue()).hexdigest()

                        buffer_fh.seek(0)
                        tile_fh.write(buffer_fh.read())
                        tiledoc[TileKeys.FILE] = str(
                            pathlib.Path(tile_fh.name).relative_to(path.parent))

                    if tile.tile_shape is not None:
                        tiledoc[TileKeys.TILE_SHAPE] = \
                            Tile.format_dict_shape_to_tuple_shape(tile.tile_shape)
                    tiledoc[TileKeys.SHA256] = tile.sha256
                    if tile_format is not None:
                        tiledoc[TileKeys.TILE_FORMAT] = tile_format.name
                    if len(tile.extras) != 0:
                        tiledoc[TileKeys.EXTRAS] = tile.extras
                    json_doc[TileSetKeys.TILES].append(tiledoc)

                return json_doc


class v0_1_0:
    VERSION = "0.1.0"

    class Reader(Reader):
        def parse(self, json_doc, baseurl, backend_config):
            if CollectionKeys.CONTENTS in json_doc:
                # this is a Collection
                result = Collection(json_doc.get(CommonPartitionKeys.EXTRAS, None))
                tp = ThreadPool()
                try:
                    func = _parse_collection(Reader.parse_doc, baseurl, backend_config)
                    results = tp.map(func, json_doc[CollectionKeys.CONTENTS].items())
                finally:
                    tp.terminate()
                for name, partition in results:
                    result.add_partition(name, partition)
            elif TileSetKeys.TILES in json_doc:
                imageformat = json_doc.get(TileSetKeys.DEFAULT_TILE_FORMAT, None)
                if imageformat is not None:
                    imageformat = ImageFormat[imageformat]

                result = TileSet(
                    tuple(json_doc[TileSetKeys.DIMENSIONS]),
                    json_doc[TileSetKeys.SHAPE],
                    json_doc.get(TileSetKeys.DEFAULT_TILE_SHAPE, None),
                    imageformat,
                    json_doc.get(TileSetKeys.EXTRAS, None),
                )

                for tile_doc in json_doc[TileSetKeys.TILES]:
                    relative_path_or_url = tile_doc[TileKeys.FILE]
                    backend, name, _ = resolve_url(relative_path_or_url, baseurl, backend_config)

                    tile_format_str = tile_doc.get(TileKeys.TILE_FORMAT, None)
                    if tile_format_str:
                        tile_format = ImageFormat[tile_format_str]
                    else:
                        tile_format = result.default_tile_format
                    if tile_format is None:
                        # Still none :(
                        extension = os.path.splitext(name)[1].lstrip(".")
                        tile_format = ImageFormat.find_by_extension(extension)
                    checksum = tile_doc.get(TileKeys.SHA256, None)
                    tile = Tile(
                        tile_doc[TileKeys.COORDINATES],
                        tile_doc[TileKeys.INDICES],
                        tile_shape=tile_doc.get(TileKeys.TILE_SHAPE, None),
                        sha256=checksum,
                        extras=tile_doc.get(TileKeys.EXTRAS, None),
                    )

                    def future_maker(_source_fh_contextmanager, _tile_format):
                        """Produces a future that reads from a file and decodes according to the
                        specified file format."""
                        def _actual_future():
                            with _source_fh_contextmanager as fh:
                                return _tile_format.reader_func(fh)

                        return _actual_future

                    tile.set_numpy_array_future(
                        future_maker(
                            backend.read_contextmanager(name, checksum_sha256=checksum),
                            tile_format))
                    result.add_tile(tile)
            else:
                raise ValueError(
                    "JSON doc does not appear to be a collection partition or a tileset "
                    "partition. JSON doc must contain either a {contents} field pointing to a "
                    "tile manifest, or it must contain a {tiles} field that specifies a set of "
                    "tiles.".format(
                        contents=CollectionKeys.CONTENTS, tiles=TileSetKeys.TILES))

            return result

    class Writer(Writer):
        def generate_partition_document(
                self,
                partition,
                path,
                pretty=False,
                partition_path_generator=Writer.default_partition_path_generator,
                tile_opener=Writer.default_tile_opener,
                tile_format=ImageFormat.NUMPY,
        ):
            if isinstance(path, str):
                warnings.warn("Paths should be passed in as pathlib.Path objects",
                              DeprecationWarning)
                path = pathlib.Path(path)

            json_doc = {
                CommonPartitionKeys.VERSION: v0_1_0.VERSION,
                CommonPartitionKeys.EXTRAS: partition.extras,
            }
            if isinstance(partition, Collection):
                json_doc[CollectionKeys.CONTENTS] = dict()
                for partition_name, partition in partition._partitions.items():
                    partition_path = partition_path_generator(path, partition_name)
                    Writer.write_to_path(
                        partition, partition_path, pretty,
                        partition_path_generator=partition_path_generator,
                        tile_opener=tile_opener,
                        tile_format=tile_format,
                    )
                    json_doc[CollectionKeys.CONTENTS][partition_name] = str(
                        partition_path.relative_to(path.parent))
                return json_doc
            elif isinstance(partition, TileSet):
                json_doc[TileSetKeys.DIMENSIONS] = tuple(partition.dimensions)
                json_doc[TileSetKeys.SHAPE] = partition.shape
                json_doc[TileSetKeys.TILES] = []

                if partition.default_tile_shape is not None:
                    json_doc[TileSetKeys.DEFAULT_TILE_SHAPE] = partition.default_tile_shape
                if partition.default_tile_format is not None:
                    json_doc[TileSetKeys.DEFAULT_TILE_FORMAT] = partition.default_tile_format.name
                if len(partition.extras) != 0:
                    json_doc[TileSetKeys.EXTRAS] = partition.extras

                for tile in partition._tiles:
                    tiledoc = {
                        TileKeys.COORDINATES: tile.coordinates,
                        TileKeys.INDICES: tile.indices,
                    }

                    with tile_opener(path, tile, tile_format.file_ext) as tile_fh:
                        buffer_fh = BytesIO()
                        tile.write(buffer_fh, tile_format)

                        buffer_fh.seek(0)
                        tile.sha256 = hashlib.sha256(buffer_fh.getvalue()).hexdigest()

                        buffer_fh.seek(0)
                        tile_fh.write(buffer_fh.read())
                        tiledoc[TileKeys.FILE] = str(
                            pathlib.Path(tile_fh.name).relative_to(path.parent))

                    if tile.tile_shape is not None:
                        tiledoc[TileKeys.TILE_SHAPE] = format_enum_keyed_dicts(tile.tile_shape)
                    tiledoc[TileKeys.SHA256] = tile.sha256
                    if tile_format is not None:
                        tiledoc[TileKeys.TILE_FORMAT] = tile_format.name
                    if len(tile.extras) != 0:
                        tiledoc[TileKeys.EXTRAS] = tile.extras
                    json_doc[TileSetKeys.TILES].append(tiledoc)

                return json_doc


VERSIONS = [
    v0_0_0,
    v0_1_0,
]
"""All the different versions of the file format, in order from oldest to newest."""


class CommonPartitionKeys:
    VERSION = "version"
    EXTRAS = "extras"


class CollectionKeys(CommonPartitionKeys):
    CONTENTS = "contents"


class TileSetKeys(CommonPartitionKeys):
    DIMENSIONS = "dimensions"
    SHAPE = "shape"
    DEFAULT_TILE_SHAPE = "default_tile_shape"
    DEFAULT_TILE_FORMAT = "default_tile_format"
    TILES = "tiles"
    ZOOM = "zoom"


class TileKeys:
    FILE = "file"
    COORDINATES = "coordinates"
    INDICES = "indices"
    TILE_SHAPE = "tile_shape"
    TILE_FORMAT = "tile_format"
    SHA256 = "sha256"
    EXTRAS = "extras"

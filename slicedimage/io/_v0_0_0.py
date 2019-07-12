import hashlib
import os
import warnings
from io import BytesIO
from multiprocessing.pool import ThreadPool

import pathlib
from packaging import version

from slicedimage._collection import Collection
from slicedimage._formats import ImageFormat
from slicedimage._tile import Tile
from slicedimage._tileset import TileSet
from slicedimage.url.resolve import resolve_url
from . import _base
from ._keys import (
    CollectionKeys,
    CommonPartitionKeys,
    TileKeys,
    TileSetKeys,
)


class v0_0_0:
    VERSION = "0.0.0"
    FIRST_UNREADABLE_VERSION = "0.1.0"

    class Reader(_base.Reader):
        @classmethod
        def can_parse(cls, doc_version: str):
            return (
                version.parse(v0_0_0.VERSION)
                <= doc_version
                < version.parse(v0_0_0.FIRST_UNREADABLE_VERSION)
            )

        def parse(self, json_doc, baseurl, backend_config):
            if CollectionKeys.CONTENTS in json_doc:
                # this is a Collection
                result = Collection(json_doc.get(CommonPartitionKeys.EXTRAS, None))
                tp = ThreadPool()
                try:
                    func = _base._parse_collection(_base.Reader.parse_doc, baseurl, backend_config)
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

    class Writer(_base.Writer):
        def generate_partition_document(
                self,
                partition,
                path,
                pretty=False,
                partition_path_generator=_base.Writer.default_partition_path_generator,
                tile_opener=_base.Writer.default_tile_opener,
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
                    _base.Writer.write_to_path(
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

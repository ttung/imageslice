import os
from multiprocessing.pool import ThreadPool
from typing import Optional, Union

from packaging import version

from slicedimage._collection import Collection
from slicedimage._formats import ImageFormat
from slicedimage._tile import Tile
from slicedimage._tileset import TileSet
from slicedimage._typeformatting import format_enum_keyed_dicts
from slicedimage.url.path import calculate_relative_url
from slicedimage.url.resolve import resolve_url
from . import _base
from ._keys import (
    CollectionKeys,
    CommonPartitionKeys,
    TileKeys,
    TileSetKeys,
)


class v0_1_0:
    VERSION = "0.1.0"
    FIRST_UNREADABLE_VERSION = "0.2.0"

    class Reader(_base.Reader):
        @classmethod
        def can_parse(cls, doc_version: str):
            return (
                version.parse(v0_1_0.VERSION)
                <= doc_version
                < version.parse(v0_1_0.FIRST_UNREADABLE_VERSION)
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

    class Writer(_base.Writer):
        def generate_partition_document(
                self,
                partition: Union[Collection, TileSet],
                url: str,
                pretty: bool = False,
                writer_contract: Optional[_base.WriterContract] = None,
                tile_format=ImageFormat.NUMPY,
                *args, **kwargs
        ):
            if writer_contract is None:
                writer_contract = _base.WriterContract()
            json_doc = {
                CommonPartitionKeys.VERSION: v0_1_0.VERSION,
                CommonPartitionKeys.EXTRAS: partition.extras,
            }
            if isinstance(partition, Collection):
                json_doc[CollectionKeys.CONTENTS] = dict()
                for partition_name, partition in partition._partitions.items():
                    partition_url = writer_contract.partition_url_generator(url, partition_name)
                    _base.Writer.write_to_url(
                        partition, partition_url, pretty,
                        writer_contract=writer_contract,
                        tile_format=tile_format,
                    )
                    json_doc[CollectionKeys.CONTENTS][partition_name] = calculate_relative_url(
                        url, partition_url)
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

                    tile_url = writer_contract.tile_url_generator(url, tile, tile_format.file_ext)
                    tiledoc[TileKeys.SHA256] = writer_contract.write_tile(
                        tile_url, tile, tile_format)
                    tiledoc[TileKeys.FILE] = calculate_relative_url(url, tile_url)

                    if tile.tile_shape is not None:
                        tiledoc[TileKeys.TILE_SHAPE] = format_enum_keyed_dicts(tile.tile_shape)
                    if tile_format is not None:
                        tiledoc[TileKeys.TILE_FORMAT] = tile_format.name
                    if len(tile.extras) != 0:
                        tiledoc[TileKeys.EXTRAS] = tile.extras
                    json_doc[TileSetKeys.TILES].append(tiledoc)

                return json_doc

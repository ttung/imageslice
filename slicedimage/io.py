from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import hashlib
import json
import os
import tempfile

from packaging import version
from six.moves import urllib

from slicedimage.urlpath import pathsplit
from .backends import DiskBackend, HttpBackend
from ._formats import ImageFormat
from ._imagepartition import ImagePartition
from ._tile import Tile
from ._tocpartition import TocPartition


def infer_backend(baseurl, allow_caching=True):
    parsed = urllib.parse.urlparse(baseurl)

    if parsed.scheme in ("http", "https"):
        backend = HttpBackend(baseurl)
    elif parsed.scheme == "file":
        backend = DiskBackend(parsed.path)
    else:
        raise ValueError("Unable to infer backend for url {}".format(baseurl))

    if allow_caching:
        # TODO: construct caching backend and return that.
        pass

    return backend


def resolve_path_or_url(path_or_url, allow_caching=True):
    """
    Given either a path (absolute or relative), or a URL, attempt to resolve it.  Returns a tuple consisting of:
    a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of the object.
    """
    try:
        return resolve_url(path_or_url, allow_caching=allow_caching)
    except ValueError:
        if os.path.isfile(path_or_url):
            return resolve_url(
                os.path.basename(path_or_url),
                baseurl="file://{}".format(os.path.dirname(os.path.abspath(path_or_url))),
                allow_caching=allow_caching,
            )
        raise


def resolve_url(name_or_url, baseurl=None, allow_caching=True):
    """
    Given a string that can either be a name or a fully qualified url, return a tuple consisting of:
    a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of the object.

    If the string is a name and not a fully qualified url, then baseurl must be set.
    """
    try:
        # assume it's a fully qualified url.
        splitted = pathsplit(name_or_url)
        backend = infer_backend(splitted[0], allow_caching)
        return backend, splitted[1], splitted[0]
    except ValueError:
        if baseurl is None:
            # oh, we have no baseurl.  punt.
            raise
        # it's not a fully qualified url.
        backend = infer_backend(baseurl, allow_caching)
        return backend, name_or_url, baseurl


class Reader(object):
    @staticmethod
    def parse_doc(name_or_url, baseurl):
        backend, name, baseurl = resolve_url(name_or_url, baseurl)
        fh = backend.read_file_handle(name)
        reader = codecs.getreader("utf-8")
        json_doc = json.load(reader(fh))

        if version.parse(json_doc[CommonPartitionKeys.VERSION]) >= version.parse(v0_0_0.VERSION):
            parser = v0_0_0.Reader()
        else:
            raise ValueError("Unrecognized version number")

        return parser.parse(json_doc, baseurl)

    def parse(self, json_doc, baseurl):
        raise NotImplementedError()


class Writer(object):
    @staticmethod
    def write_to_path(imagestack, path, pretty=False, *args, **kwargs):
        document = v0_0_0.Writer().generate_toc(imagestack, path, *args, **kwargs)
        indent = 4 if pretty else None
        with open(path, "w") as fh:
            json.dump(document, fh, indent=indent, sort_keys=pretty)

    @staticmethod
    def default_toc_path_generator(toc_path):
        toc_basename = os.path.splitext(os.path.basename(toc_path))[0]
        return tempfile.NamedTemporaryFile(
            suffix=".json",
            prefix="{}-".format(toc_basename),
            dir=os.path.dirname(toc_path),
            delete=False,
        )

    @staticmethod
    def default_tile_opener(toc_path, tile, ext):
        tile_basename = os.path.splitext(os.path.basename(toc_path))[0]
        return tempfile.NamedTemporaryFile(
            suffix=".{}".format(ext),
            prefix="{}-".format(tile_basename),
            dir=os.path.dirname(toc_path),
            delete=False,
        )

    @staticmethod
    def default_tile_writer(tile, fh):
        tile.write(fh)
        return ImageFormat.NUMPY

    def generate_toc(self, imagestack, path, *args, **kwargs):
        raise NotImplementedError()


class v0_0_0(object):
    VERSION = "0.0.0"

    class Reader(Reader):
        def parse(self, json_doc, baseurl):
            if TocPartitionKeys.TOCS in json_doc:
                # this is a TocPartition
                result = TocPartition(json_doc.get(CommonPartitionKeys.EXTRAS, None))
                for name_or_url in json_doc[TocPartitionKeys.TOCS]:
                    toc = Reader.parse_doc(name_or_url, baseurl)
                    toc._name_or_url = name_or_url
                    result.add_toc(toc)
            elif ImagePartitionKeys.TILES in json_doc:
                imageformat = json_doc.get(ImagePartitionKeys.DEFAULT_TILE_FORMAT, None)
                if imageformat is not None:
                    imageformat = ImageFormat[imageformat]
                result = ImagePartition(
                    tuple(json_doc[ImagePartitionKeys.DIMENSIONS]),
                    json_doc[ImagePartitionKeys.SHAPE],
                    json_doc.get(ImagePartitionKeys.DEFAULT_TILE_SHAPE, None),
                    imageformat,
                    json_doc.get(ImagePartitionKeys.EXTRAS, None),
                )

                for tile_doc in json_doc[ImagePartitionKeys.TILES]:
                    name_or_url = tile_doc[TileKeys.FILE]
                    backend, name, _ = resolve_url(name_or_url, baseurl)

                    tile_format_str = tile_doc.get(TileKeys.TILE_FORMAT, None)
                    if tile_format_str:
                        tile_format = ImageFormat[tile_format_str]
                    else:
                        tile_format = result.default_tile_format
                    if tile_format is None:
                        # Still none :(
                        extension = os.path.splitext(name)[1]
                        tile_format = ImageFormat.find_by_extension(extension)

                    tile = Tile(
                        tile_doc[TileKeys.COORDINATES],
                        tile_doc[TileKeys.INDICES],
                        tile_shape=tile_doc.get(TileKeys.TILE_SHAPE, None),
                        sha256=tile_doc.get(TileKeys.SHA256, None),
                        extras=tile_doc.get(TileKeys.EXTRAS, None),
                    )
                    tile.set_source_fh_contextmanager(backend.read_file_handle_callable(name), tile_format)
                    tile._file_or_url = name_or_url
                    result.add_tile(tile)
            else:
                raise ValueError("json doc does not appear to be a TOC partition or an image partition")

            return result

    class Writer(Writer):
        def generate_toc(
                self,
                imagestack,
                path,
                toc_path_generator=Writer.default_toc_path_generator,
                tile_opener=Writer.default_tile_opener,
                tile_writer=Writer.default_tile_writer):
            json_doc = {
                CommonPartitionKeys.VERSION: v0_0_0.VERSION,
                CommonPartitionKeys.EXTRAS: imagestack.extras,
            }
            if isinstance(imagestack, TocPartition):
                for toc in imagestack._tocs:
                    tocpath = toc_path_generator(path, toc)
                    Writer.write_to_path(
                        toc, tocpath,
                        toc_path_generator=toc_path_generator,
                        tile_opener=tile_opener,
                        tile_Writer=tile_writer
                    )
                return json_doc
            elif isinstance(imagestack, ImagePartition):
                json_doc[ImagePartitionKeys.DIMENSIONS] = tuple(imagestack.dimensions)
                json_doc[ImagePartitionKeys.SHAPE] = imagestack.shape
                json_doc[ImagePartitionKeys.TILES] = []

                if imagestack.default_tile_shape is not None:
                    json_doc[ImagePartitionKeys.DEFAULT_TILE_SHAPE] = imagestack.default_tile_shape
                if imagestack.default_tile_format is not None:
                    json_doc[ImagePartitionKeys.DEFAULT_TILE_FORMAT] = imagestack.default_tile_format.name
                if len(imagestack.extras) != 0:
                    json_doc[ImagePartitionKeys.EXTRAS] = imagestack.extras

                for tile in imagestack._tiles:
                    tiledoc = {
                        TileKeys.COORDINATES: tile.coordinates,
                        TileKeys.INDICES: tile.indices,
                    }

                    with tile_opener(path, tile, ImageFormat.NUMPY.file_ext) as tile_fh:
                        if tile.sha256 is None:
                            hasher_fh = HashFile(hashlib.sha256)
                            writer_fh = TeeWritableFileObject(tile_fh, hasher_fh)
                        else:
                            hasher_fh = None
                            writer_fh = tile_fh
                        tile_format = tile_writer(tile, writer_fh)
                        tiledoc[TileKeys.FILE] = os.path.basename(tile_fh.name)
                        if hasher_fh is not None:
                            tile.sha256 = hasher_fh.hexdigest().lower()

                    if tile.tile_shape is not None:
                        tiledoc[TileKeys.TILE_SHAPE] = tile.tile_shape
                    tiledoc[TileKeys.SHA256] = tile.sha256
                    if tile_format is not None:
                        tiledoc[TileKeys.TILE_FORMAT] = tile_format.name
                    if len(tile.extras) != 0:
                        tiledoc[TileKeys.EXTRAS] = tile.extras
                    json_doc[ImagePartitionKeys.TILES].append(tiledoc)

                return json_doc


class HashFile(object):
    def __init__(self, hash_constructor):
        self.hasher = hash_constructor()

    def write(self, data):
        self.hasher.update(data)
        return len(data)

    def digest(self):
        return self.hasher.digest()

    def hexdigest(self):
        return self.hasher.hexdigest()


class TeeWritableFileObject(object):
    def __init__(self, *backingfiles):
        self.backingfiles = backingfiles

    def write(self, data):
        for backingfile in self.backingfiles:
            backingfile.write(data)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class CommonPartitionKeys(object):
    VERSION = "version"
    EXTRAS = "extras"


class TocPartitionKeys(CommonPartitionKeys):
    TOCS = "tocs"


class ImagePartitionKeys(CommonPartitionKeys):
    DIMENSIONS = "dimensions"
    SHAPE = "shape"
    DEFAULT_TILE_SHAPE = "default_tile_shape"
    DEFAULT_TILE_FORMAT = "default_tile_format"
    TILES = "tiles"
    ZOOM = "zoom"


class TileKeys(object):
    FILE = "file"
    COORDINATES = "coordinates"
    INDICES = "indices"
    TILE_SHAPE = "tile_shape"
    TILE_FORMAT = "tile_format"
    SHA256 = "sha256"
    EXTRAS = "extras"

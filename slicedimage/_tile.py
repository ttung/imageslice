from __future__ import absolute_import, division, print_function, unicode_literals

from six import BytesIO

from ._formats import ImageFormat
from ._typeformatting import format_tile_dimensions


class Tile(object):
    def __init__(self, coordinates, indices, tile_shape=None, sha256=None, extras=None):
        self.coordinates = format_tile_dimensions(coordinates)
        self.indices = format_tile_dimensions(indices)
        self.tile_shape = tuple(tile_shape) if tile_shape is not None else None
        self.sha256 = sha256
        self.extras = {} if extras is None else extras

        self.tile_format = None
        self._source_fh_contextmanager = None
        self._numpy_array = None
        self._name_or_url = None

    def _load(self):
        if self._source_fh_contextmanager is not None:
            assert self._numpy_array is None, "Inconsistent state.  Tile should only have one data source."
            with self._source_fh_contextmanager() as src_fh:
                self._numpy_array = self.tile_format.reader_func(src_fh)
            self._source_fh_contextmanager = None
            self.tile_format = ImageFormat.NUMPY

    @property
    def numpy_array(self):
        self._load()
        return self._numpy_array

    @numpy_array.setter
    def numpy_array(self, numpy_array):
        if self.tile_shape is not None:
            assert self.tile_shape == numpy_array.shape

        self._source_fh_contextmanager = None
        self._numpy_array = numpy_array
        self.tile_format = ImageFormat.NUMPY

    def set_source_fh_contextmanager(self, source_fh_contextmanager, tile_format):
        """
        Provides a tile with a callable, which should yield a context manager that returns a file-like object.  If the
        tile data is requested, the context manager is invoked and the data is read from the returned file-like object.
        It is possible that the context manager is never invoked.
        """
        self._source_fh_contextmanager = source_fh_contextmanager
        self._numpy_array = None
        self.tile_format = tile_format

    def write(self, dst_fh):
        """
        Write the contents of this tile out to a given file handle.
        """
        import numpy

        self._load()

        numpy.save(dst_fh, self._numpy_array)

    def copy(self, dst_fh):
        """
        Write the contents of this tile out to a given file handle, in the original file format provided.
        """
        if self._source_fh_contextmanager is not None:
            assert self._numpy_array is None
            with self._source_fh_contextmanager() as src_fh:
                data = src_fh.read()
                self._numpy_array = self.tile_format.reader_func(BytesIO(data))
                dst_fh.write(data)
            self._source_fh_contextmanager = None
            self.tile_format = ImageFormat.NUMPY
        else:
            raise RuntimeError("copy can only be called on a tile that hasn't been decoded.")

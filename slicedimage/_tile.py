from __future__ import absolute_import, division, print_function, unicode_literals

from ._typeformatting import format_tile_coordinates, format_tile_indices


class Tile(object):
    def __init__(self, coordinates, indices, tile_shape=None, sha256=None, extras=None):
        self.coordinates = format_tile_coordinates(coordinates)
        self.indices = format_tile_indices(indices)
        self.tile_shape = tuple(tile_shape) if tile_shape is not None else None
        self.sha256 = sha256
        self.extras = {} if extras is None else extras

        self._numpy_array = None
        self._numpy_array_future = None

    def _load(self):
        if self._numpy_array_future is not None:
            assert self._numpy_array is None, (
                "Inconsistent state.  Tile should only have one data source.")
            self._numpy_array = self._numpy_array_future()
            self._numpy_array_future = None
            self.tile_shape = self.numpy_array.shape

    @property
    def numpy_array(self):
        self._load()
        return self._numpy_array

    @numpy_array.setter
    def numpy_array(self, numpy_array):
        if self.tile_shape is not None:
            assert self.tile_shape == numpy_array.shape

        self._numpy_array = numpy_array
        self.tile_shape = self._numpy_array.shape
        self._numpy_array_future = None

    def set_numpy_array_future(self, future):
        """
        Provides a tile with a callable, which should return the tile data when invoked.  It is
        possible that the future is never invoked.

        Parameters
        ----------
        future : Callable[[], np.ndarray]
            A callable that yields the tile data when invoked.
        """
        self._numpy_array_future = future
        self._numpy_array = None

    def write(self, dst_fh, tile_format):
        """
        Write the contents of this tile out to a given file handle.
        """
        self._load()

        tile_format.writer_func(dst_fh, self._numpy_array)

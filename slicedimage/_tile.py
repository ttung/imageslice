from __future__ import absolute_import, division, print_function, unicode_literals

import warnings

from ._dimensions import DimensionNames
from ._typeformatting import format_enum_keyed_dicts, format_tile_coordinates


class Tile(object):
    def __init__(self, coordinates, indices, tile_shape=None, sha256=None, extras=None):
        self.coordinates = format_tile_coordinates(coordinates)
        self.indices = format_enum_keyed_dicts(indices)
        self._tile_shape = format_enum_keyed_dicts(tile_shape) if tile_shape is not None else None
        self.sha256 = sha256
        self.extras = {} if extras is None else extras

        self._numpy_array = None
        self._numpy_array_future = None

    @staticmethod
    def format_tuple_shape_to_dict_shape(tuple_shape):
        if tuple_shape is None:
            return None
        return {DimensionNames.Y: tuple_shape[-2], DimensionNames.X: tuple_shape[-1]}

    @staticmethod
    def format_dict_shape_to_tuple_shape(dict_shape):
        if dict_shape is None:
            return None
        return dict_shape[DimensionNames.Y], dict_shape[DimensionNames.X]

    @property
    def tile_shape(self):
        if self._tile_shape is None:
            warnings.warn(
                "Decoding tile just to obtain shape.  It is recommended to include the tile shape "
                "in the tileset document to avoid this."
            )
            shape = self._numpy_array_future().shape
            self._tile_shape = Tile.format_tuple_shape_to_dict_shape(shape)

        return self._tile_shape

    @property
    def numpy_array(self):
        if self._numpy_array is not None:
            return self._numpy_array
        else:
            result = self._numpy_array_future()

            if self._tile_shape is not None:
                assert Tile.format_dict_shape_to_tuple_shape(self._tile_shape) == result.shape
            else:
                self._tile_shape = Tile.format_tuple_shape_to_dict_shape(result.shape)

            return result

    @numpy_array.setter
    def numpy_array(self, numpy_array):
        if self._tile_shape is not None:
            assert Tile.format_dict_shape_to_tuple_shape(self._tile_shape) == numpy_array.shape
        else:
            self._tile_shape = Tile.format_tuple_shape_to_dict_shape(numpy_array.shape)

        self._numpy_array = numpy_array
        self._numpy_array_future = None

    def set_numpy_array_future(self, future):
        """
        Provides a tile with a callable, which should return the tile data when invoked.  It should
        be possible to invoke the callable 0, 1, or many times.

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
        tile_format.writer_func(dst_fh, self.numpy_array)

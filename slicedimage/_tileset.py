from __future__ import absolute_import, division, print_function, unicode_literals

from itertools import chain

from ._typeformatting import format_tileset_dimensions, format_tileset_shape


class TileSet(object):
    def __init__(
            self,
            dimensions,
            shape,
            default_tile_shape=None,
            default_tile_format=None,
            extras=None):
        self.dimensions = format_tileset_dimensions(dimensions)
        self.shape = format_tileset_shape(shape)
        self.default_tile_shape = None if default_tile_shape is None else tuple(default_tile_shape)
        self.default_tile_format = default_tile_format
        self.extras = {} if extras is None else extras
        self._tiles = []

        self._discrete_dimensions = set()

    def __repr__(self):
        # get dimensions of optional shapes
        shapes = (
            "{k}: {v}".format(k=k, v=self.shape[k])
            for k in self.dimensions - {'y', 'x'}
        )
        # get dimensions of x and y
        tile_dimensions = (
            "y: {y}".format(y=self.default_tile_shape[1]),
            "x: {x}".format(x=self.default_tile_shape[0])
        )
        shape = ", ".join(chain(shapes, tile_dimensions))
        return "<slicedimage.TileSet ({shape})>".format(shape=shape)

    def validate(self):
        raise NotImplementedError()

    def add_tile(self, tile):
        self._tiles.append(tile)

    def tiles(self, filter_fn=lambda _: True):
        """
        Return the tiles in this tileset.  If a filter_fn is provided, only the tiles for which
        filter_fn returns True are returned.
        """
        return list(filter(filter_fn, self._tiles))

    def get_dimension_shape(self, dimension_name):
        return self.shape[dimension_name]

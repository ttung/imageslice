from __future__ import absolute_import, division, print_function, unicode_literals

from ._dimensions import DimensionNames
from ._typeformatting import (
    format_enum_keyed_dicts,
    format_tileset_dimensions,
    format_tileset_shape,
)


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
        self.default_tile_shape = (format_enum_keyed_dicts(default_tile_shape)
                                   if default_tile_shape is not None else None)
        self.default_tile_format = default_tile_format
        self.extras = {} if extras is None else extras
        self._tiles = []

        self._discrete_dimensions = set()

    def __repr__(self):
        # get dimensions of optional shapes
        attributes = [
            "{k}: {v}".format(k=k, v=self.shape[k])
            for k in self.dimensions - {DimensionNames.Y, DimensionNames.X}
            if k in self.shape
        ]
        xmin, xmax, ymin, ymax = float("inf"), float("-inf"), float("inf"), float("-inf")
        for tile in self._tiles:
            # try to get the shape in the following order:
            # 1. read the tile's declared shape without forcing a read & decode of the tile data.
            # 2. read the tileset's default tile shape.
            # 3. read the tile's shape through a read & decode.
            shape = tile._tile_shape
            if shape is None:
                shape = self.default_tile_shape
            if shape is None:
                shape = tile.tile_shape

            xmin = min(xmin, shape[DimensionNames.X])
            xmax = max(xmax, shape[DimensionNames.X])
            ymin = min(ymin, shape[DimensionNames.Y])
            ymax = max(ymax, shape[DimensionNames.Y])

        if xmin == xmax:
            attributes.append("x: {}".format(xmin))
        else:
            attributes.append("x: ({}-{})".format(xmin, xmax))
        if ymin == ymax:
            attributes.append("y: {}".format(ymin))
        else:
            attributes.append("y: ({}-{})".format(ymin, ymax))

        shape = ", ".join(attributes)
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

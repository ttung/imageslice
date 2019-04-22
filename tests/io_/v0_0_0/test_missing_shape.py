import codecs
import json
import os
import tempfile
import unittest
import warnings

import numpy as np

import slicedimage
from slicedimage._dimensions import DimensionNames
from slicedimage.io import TileKeys, TileSetKeys
from tests.utils import TemporaryDirectory

baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestMissingShape(unittest.TestCase):
    def test_tileset_without_shapes(self):
        image = slicedimage.TileSet(
            [DimensionNames.X, DimensionNames.Y, "ch", "hyb"],
            {'ch': 2, 'hyb': 2},
        )

        for hyb in range(2):
            for ch in range(2):
                tile = slicedimage.Tile(
                    {
                        DimensionNames.X: (0.0, 0.01),
                        DimensionNames.Y: (0.0, 0.01),
                    },
                    {
                        'hyb': hyb,
                        'ch': ch,
                    },
                )
                tile.numpy_array = np.zeros((120, 80))
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                image, partition_file.name)

            # remove the shape information from the tiles.
            for tile in partition_doc[TileSetKeys.TILES]:
                del tile[TileKeys.TILE_SHAPE]

            writer = codecs.getwriter("utf-8")
            json.dump(partition_doc, writer(partition_file))
            partition_file.flush()

            basename = os.path.basename(partition_file.name)
            baseurl = "file://{}".format(os.path.dirname(partition_file.name))

            loaded = slicedimage.Reader.parse_doc(basename, baseurl)

            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(
                                 lambda tile: (tile.indices['hyb'] == hyb and
                                               tile.indices['ch'] == ch))]

                    self.assertEqual(len(tiles), 1)
                    with warnings.catch_warnings(record=True) as w:
                        # Cause all warnings to always be triggered.  Duplicate warnings are
                        # normally suppressed.
                        warnings.simplefilter("always")

                        tile_shape = tiles[0].tile_shape

                        self.assertEqual(tile_shape, {DimensionNames.Y: 120, DimensionNames.X: 80})
                        self.assertEqual(len(w), 1)
                        self.assertIn("Decoding tile just to obtain shape", str(w[0].message))

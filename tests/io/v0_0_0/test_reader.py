import collections
import os
import unittest

import slicedimage


baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestReader(unittest.TestCase):
    def test_read_tileset(self):
        result = slicedimage.Reader.parse_doc("tileset.json", baseurl)
        self.assertIsInstance(result, slicedimage.TileSet)
        self.assertEqual(result.shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def test_read_collection(self):
        result = slicedimage.Reader.parse_doc("collection_l1.json", baseurl)
        self.assertIsInstance(result, slicedimage.Collection)
        tileset = result.find_tileset("fov_001")
        self.assertEqual(tileset.shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def test_read_multilevel_collection(self):
        result = slicedimage.Reader.parse_doc("collection_l2.json", baseurl)
        self.assertIsInstance(result, slicedimage.Collection)
        tileset = result.find_tileset("fov_001")
        self.assertEqual(tileset.shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def _verify_tiles(self, tile_generator):
        tiles = [tile for tile in tile_generator]
        self.assertEqual(len(tiles), 16)

        for hyb in range(4):
            for ch in range(4):
                for tile in tiles:
                    if tile.indices['hyb'] == hyb and tile.indices['ch'] == ch:
                        break
                else:
                    self.fail("Couldn't find tile of hyb {} ch {}".format(hyb, ch))

        for tile in tiles:
            for value in tile.coordinates.values():
                self.assertTrue(isinstance(value, collections.Hashable))
            for value in tile.indices.values():
                self.assertTrue(isinstance(value, collections.Hashable))

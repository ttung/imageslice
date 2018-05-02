import collections
import os
import sys
import unittest


pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa


import slicedimage


baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestReader(unittest.TestCase):
    def test_read_imagepartition(self):
        result = slicedimage.Reader.parse_doc("imagepartition.json", baseurl)
        self.assertIsInstance(result, slicedimage.ImagePartition)
        self.assertEqual(result.shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def test_read_tocpartition(self):
        result = slicedimage.Reader.parse_doc("tocpartition_l1.json", baseurl)
        self.assertIsInstance(result, slicedimage.TocPartition)
        self.assertEqual(len(result.all_tocs()), 1)
        self.assertEqual(result.all_tocs()[0].shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def test_read_multilevel_tpartition(self):
        result = slicedimage.Reader.parse_doc("tocpartition_l2.json", baseurl)
        self.assertIsInstance(result, slicedimage.TocPartition)
        self.assertEqual(len(result.all_tocs()), 1)
        self.assertEqual(result.all_tocs()[0].shape, {'hyb': 4, 'ch': 4})
        self._verify_tiles(result.tiles())

    def _verify_tiles(self, tiles):
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

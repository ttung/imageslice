import codecs
import json
import numpy
import os
import sys
import tempfile
import unittest


pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa


import slicedimage
from tests.utils import TemporaryDirectory


baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestWrite(unittest.TestCase):
    def test_write_tileset(self):
        image = slicedimage.TileSet(
            ["x", "y", "ch", "hyb"],
            {'ch': 2, 'hyb': 2},
            (100, 100),
        )

        for hyb in range(2):
            for ch in range(2):
                tile = slicedimage.Tile(
                    {
                        'x': (0.0, 0.01),
                        'y': (0.0, 0.01),
                    },
                    {
                        'hyb': hyb,
                        'ch': ch,
                    },
                )
                tile.numpy_array = numpy.zeros((100, 100))
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(image, partition_file.name)
            writer = codecs.getwriter("utf-8")
            json.dump(partition_doc, writer(partition_file))
            partition_file.flush()

            basename = os.path.basename(partition_file.name)
            baseurl = "file://{}".format(os.path.dirname(partition_file.name))

            loaded = slicedimage.Reader.parse_doc(basename, baseurl)

            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(lambda tile:
                                                       tile.indices['hyb'] == hyb and tile.indices['ch'] == ch)]

                    self.assertEqual(len(tiles), 1)

                    expected = numpy.zeros((100, 100))
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)

    def test_write_collection(self):
        image = slicedimage.TileSet(
            ["x", "y", "ch", "hyb"],
            {'ch': 2, 'hyb': 2},
            (100, 100),
        )

        for hyb in range(2):
            for ch in range(2):
                tile = slicedimage.Tile(
                    {
                        'x': (0.0, 0.01),
                        'y': (0.0, 0.01),
                    },
                    {
                        'hyb': hyb,
                        'ch': ch,
                    },
                )
                tile.numpy_array = numpy.zeros((100, 100))
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)
        collection = slicedimage.Collection()
        collection.add_partition("fov002", image)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(collection, partition_file.name)
            writer = codecs.getwriter("utf-8")
            json.dump(partition_doc, writer(partition_file))
            partition_file.flush()

            basename = os.path.basename(partition_file.name)
            baseurl = "file://{}".format(os.path.dirname(partition_file.name))

            loaded = slicedimage.Reader.parse_doc(basename, baseurl)

            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(lambda tile:
                                                       tile.indices['hyb'] == hyb and tile.indices['ch'] == ch)]

                    self.assertEqual(len(tiles), 1)

                    expected = numpy.zeros((100, 100))
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)

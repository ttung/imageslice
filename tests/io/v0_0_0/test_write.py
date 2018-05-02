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
    def test_write_imagepartition(self):
        image = slicedimage.ImagePartition(
            ["x", "y", "ch", "hyb"],
            (2, 2),
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

        with TemporaryDirectory() as tempdir, tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as toc_file:
            toc_doc = slicedimage.v0_0_0.Writer().generate_toc(image, toc_file.name)
            writer = codecs.getwriter("utf-8")
            json.dump(toc_doc, writer(toc_file))
            toc_file.flush()

            basename = os.path.basename(toc_file.name)
            baseurl = "file://{}".format(os.path.dirname(toc_file.name))

            loaded = slicedimage.Reader.parse_doc(basename, baseurl)

            for hyb in range(2):
                for ch in range(2):
                    tiles = loaded.tiles(
                        lambda tile: tile.indices['hyb'] == hyb and tile.indices['ch'] == ch)

                    self.assertEqual(len(tiles), 1)

                    expected = numpy.zeros((100, 100))
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())

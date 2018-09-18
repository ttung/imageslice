import codecs
import hashlib
import json
import os
import tempfile
import unittest

import numpy as np
import skimage.io

import slicedimage
from slicedimage import ImageFormat
from tests.utils import TemporaryDirectory, build_skeleton_manifest

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
                tile.numpy_array = np.zeros((100, 100))
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                image, partition_file.name)
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

                    expected = np.zeros((100, 100))
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
                tile.numpy_array = np.zeros((100, 100))
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)
        collection = slicedimage.Collection()
        collection.add_partition("fov002", image)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                collection, partition_file.name)
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

                    expected = np.zeros((100, 100))
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)

    def test_checksum_on_write(self):
        """
        Generate a tileset consisting of a single TIFF tile.  Load it and then write it back out
        as a numpy tile, which should be written with different checksums.  Then verify that the
        numpy version can load without an error.
        """
        # write the tiff file
        with TemporaryDirectory() as tempdir:
            data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
            file_path = os.path.join(tempdir, "tile.tiff")
            skimage.io.imsave(file_path, data, plugin="tifffile")
            with open(file_path, "rb") as fh:
                checksum = hashlib.sha256(fh.read()).hexdigest()

            manifest = build_skeleton_manifest()
            manifest['tiles'].append(
                {
                    "coordinates": {
                        "x": [
                            0.0,
                            0.0001,
                        ],
                        "y": [
                            0.0,
                            0.0001,
                        ]
                    },
                    "indices": {
                        "hyb": 0,
                        "ch": 0,
                    },
                    "file": "tile.tiff",
                    "format": "tiff",
                    "sha256": checksum,
                },
            )
            with open(os.path.join(tempdir, "tileset.json"), "w") as fh:
                fh.write(json.dumps(manifest))

            image = slicedimage.Reader.parse_doc(
                "tileset.json",
                "file://{}".format(tempdir),
                allow_caching=False,
            )

            with TemporaryDirectory() as output_tempdir, \
                    tempfile.NamedTemporaryFile(
                        suffix=".json", dir=output_tempdir) as partition_file:
                partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                    image, partition_file.name)

                writer = codecs.getwriter("utf-8")
                json.dump(partition_doc, writer(partition_file))
                partition_file.flush()

                basename = os.path.basename(partition_file.name)
                baseurl = "file://{}".format(os.path.dirname(partition_file.name))

                loaded = slicedimage.Reader.parse_doc(basename, baseurl)

                loaded.tiles()[0]._load()

    def test_write_tiff(self):
        image = slicedimage.TileSet(
            dimensions=["x", "y", "ch", "hyb"],
            shape={'ch': 2, 'hyb': 2},
            default_tile_shape=(100, 100),
        )

        for hyb in range(2):
            for ch in range(2):
                tile = slicedimage.Tile(
                    coordinates={
                        'x': (0.0, 0.01),
                        'y': (0.0, 0.01),
                    },
                    indices={
                        'hyb': hyb,
                        'ch': ch,
                    },
                )
                tile.numpy_array = np.zeros((100, 100), dtype=np.uint32)
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)

        with TemporaryDirectory() as tempdir, \
                tempfile.NamedTemporaryFile(suffix=".json", dir=tempdir) as partition_file:
            # create the tileset and save it.
            partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                image, partition_file.name, tile_format=ImageFormat.TIFF)
            writer = codecs.getwriter("utf-8")
            json.dump(partition_doc, writer(partition_file))
            partition_file.flush()

            # construct a URL to the tileset we wrote, and load the tileset.
            basename = os.path.basename(partition_file.name)
            baseurl = "file://{}".format(os.path.dirname(partition_file.name))
            loaded = slicedimage.Reader.parse_doc(basename, baseurl)

            # compare the tiles we loaded to the tiles we set up.
            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(
                                 lambda tile: (tile.indices['hyb'] == hyb and
                                               tile.indices['ch'] == ch))]

                    self.assertEqual(len(tiles), 1)

                    expected = np.zeros((100, 100), dtype=np.uint32)
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)

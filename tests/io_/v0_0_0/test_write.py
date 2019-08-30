import codecs
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import tifffile
import numpy as np
from slicedimage._compat import fspath

import slicedimage
from slicedimage import ImageFormat
from slicedimage._dimensions import DimensionNames
from tests.utils import build_skeleton_manifest

baseurl = Path(__file__).parent.resolve().as_uri()


class TestWrite(unittest.TestCase):
    def test_write_tileset(self):
        image = slicedimage.TileSet(
            [DimensionNames.X, DimensionNames.Y, "ch", "hyb"],
            {'ch': 2, 'hyb': 2},
            {DimensionNames.Y: 120, DimensionNames.X: 80},
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

        with tempfile.TemporaryDirectory() as tempdir:
            with tempfile.NamedTemporaryFile(
                    suffix=".json", dir=tempdir, delete=False) as partition_file:
                partition_file_path = Path(partition_file.name)
                partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                    image, partition_file_path.as_uri())
                writer = codecs.getwriter("utf-8")
                json.dump(partition_doc, writer(partition_file))

            loaded = slicedimage.Reader.parse_doc(
                partition_file_path.name, partition_file_path.parent.as_uri())

            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(
                                 lambda tile: (
                                     tile.indices['hyb'] == hyb
                                     and tile.indices['ch'] == ch))]

                    self.assertEqual(len(tiles), 1)

                    expected = np.zeros((100, 100))
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)

    def test_write_collection(self):
        image = slicedimage.TileSet(
            [DimensionNames.X, DimensionNames.Y, "ch", "hyb"],
            {'ch': 2, 'hyb': 2},
            {DimensionNames.Y: 120, DimensionNames.X: 80},
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
        collection = slicedimage.Collection()
        collection.add_partition("fov002", image)

        with tempfile.TemporaryDirectory() as tempdir:
            with tempfile.NamedTemporaryFile(
                    suffix=".json", dir=tempdir, delete=False) as partition_file:
                partition_file_path = Path(partition_file.name)
                partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                    collection, partition_file_path.as_uri())
                writer = codecs.getwriter("utf-8")
                json.dump(partition_doc, writer(partition_file))

            loaded = slicedimage.Reader.parse_doc(
                partition_file_path.name, partition_file_path.parent.as_uri())

            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(
                                 lambda tile: (
                                     tile.indices['hyb'] == hyb
                                     and tile.indices['ch'] == ch))]

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
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir_path = Path(tempdir)
            file_path = tempdir_path / "tile.tiff"
            data = np.random.randint(0, 65535, size=(120, 80), dtype=np.uint16)
            with tifffile.TiffWriter(fspath(file_path)) as tiff:
                tiff.save(data)
            with open(fspath(file_path), "rb") as fh:
                checksum = hashlib.sha256(fh.read()).hexdigest()

            manifest = build_skeleton_manifest()
            manifest['tiles'].append(
                {
                    "coordinates": {
                        DimensionNames.X.value: [
                            0.0,
                            0.0001,
                        ],
                        DimensionNames.Y.value: [
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
            with open(fspath(tempdir_path / "tileset.json"), "w") as fh:
                fh.write(json.dumps(manifest))

            image = slicedimage.Reader.parse_doc(
                "tileset.json",
                tempdir_path.as_uri(),
                {"cache": {"size_limit": 0}},  # disabled
            )

            with tempfile.TemporaryDirectory() as output_tempdir:
                with tempfile.NamedTemporaryFile(
                        suffix=".json", dir=output_tempdir, delete=False) as partition_file:
                    partition_file_path = Path(partition_file.name)
                    partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                        image, partition_file_path.as_uri())

                    writer = codecs.getwriter("utf-8")
                    json.dump(partition_doc, writer(partition_file))

                loaded = slicedimage.Reader.parse_doc(
                    partition_file_path.name, partition_file_path.parent.as_uri())

                loaded.tiles()[0].numpy_array

    def test_write_tiff(self):
        image = slicedimage.TileSet(
            dimensions=[DimensionNames.X, DimensionNames.Y, "ch", "hyb"],
            shape={'ch': 2, 'hyb': 2},
            default_tile_shape={DimensionNames.Y: 120, DimensionNames.X: 80},
        )

        for hyb in range(2):
            for ch in range(2):
                tile = slicedimage.Tile(
                    coordinates={
                        DimensionNames.X: (0.0, 0.01),
                        DimensionNames.Y: (0.0, 0.01),
                    },
                    indices={
                        'hyb': hyb,
                        'ch': ch,
                    },
                )
                tile.numpy_array = np.zeros((120, 80), dtype=np.uint32)
                tile.numpy_array[hyb, ch] = 1
                image.add_tile(tile)

        with tempfile.TemporaryDirectory() as tempdir:
            with tempfile.NamedTemporaryFile(
                    suffix=".json", dir=tempdir, delete=False) as partition_file:
                # create the tileset and save it.
                partition_file_path = Path(partition_file.name)
                partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
                    image, partition_file_path.as_uri(), tile_format=ImageFormat.TIFF)
                writer = codecs.getwriter("utf-8")
                json.dump(partition_doc, writer(partition_file))

            # construct a URL to the tileset we wrote, and load the tileset.
            loaded = slicedimage.Reader.parse_doc(
                partition_file_path.name, partition_file_path.parent.as_uri())

            # compare the tiles we loaded to the tiles we set up.
            for hyb in range(2):
                for ch in range(2):
                    tiles = [_tile
                             for _tile in loaded.tiles(
                                 lambda tile: (
                                     tile.indices['hyb'] == hyb
                                     and tile.indices['ch'] == ch))]

                    self.assertEqual(len(tiles), 1)

                    expected = np.zeros((120, 80), dtype=np.uint32)
                    expected[hyb, ch] = 1

                    self.assertEqual(tiles[0].numpy_array.all(), expected.all())
                    self.assertIsNotNone(tiles[0].sha256)


if __name__ == "__main__":
    unittest.main()

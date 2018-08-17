import json
import os
import sys
import time
import unittest

import numpy as np
import requests
import skimage.io


pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import slicedimage
from tests.utils import build_skeleton_manifest, ContextualChildProcess, \
    TemporaryDirectory, unused_tcp_port


class TestHttpBackend(unittest.TestCase):
    def setUp(self, timeout_seconds=5):
        self.contexts = []
        self.tempdir = TemporaryDirectory()
        self.contexts.append(self.tempdir)
        self.port = unused_tcp_port()

        if sys.version_info[0] == 2:
            module = "SimpleHTTPServer"
        elif sys.version_info[0] == 3:
            module = "http.server"
        else:
            raise Exception("unknown python version")

        self.contexts.append(ContextualChildProcess(
            [
                "python",
                "-m",
                module,
                str(self.port),
            ],
            cwd=self.tempdir.name,
        ).__enter__())

        end = time.time() + timeout_seconds
        while True:
            try:
                requests.get("http://0.0.0.0:{port}".format(port=self.port))
                break
            except requests.ConnectionError:
                if time.time() > end:
                    raise

    def tearDown(self):
        for context in self.contexts:
            context.__exit__(*sys.exc_info())

    def test_tiff(self):
        """
        Generate a tileset consisting of a single TIFF tile.  Deposit it where the HTTP server can
        find the tileset, and fetch it.
        """
        # write the tiff file
        data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        skimage.io.imsave(os.path.join(self.tempdir.name, "tile.tiff"), data, plugin="tifffile")

        # TODO: (ttung) We should really be producing a tileset programmatically and writing it
        # disk.  However, our current write path only produces numpy output files.
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
            },
        )
        with open(os.path.join(self.tempdir.name, "tileset.json"), "w") as fh:
            fh.write(json.dumps(manifest))

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))

    def test_numpy(self):
        """
        Generate a tileset consisting of a single NUMPY tile.  Deposit it where the HTTP server can
        find the tileset, and fetch it.
        """
        image = slicedimage.TileSet(
            ["x", "y", "ch", "hyb"],
            {'ch': 1, 'hyb': 1},
            (100, 100),
        )

        tile = slicedimage.Tile(
            {
                'x': (0.0, 0.01),
                'y': (0.0, 0.01),
            },
            {
                'hyb': 0,
                'ch': 0,
            },
        )
        tile.numpy_array = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        image.add_tile(tile)

        partition_path = os.path.join(self.tempdir.name, "tileset.json")
        partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
            image, partition_path)
        with open(partition_path, "w") as fh:
            json.dump(partition_doc, fh)

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, tile.numpy_array))

    def test_numpy_requires_seekable(self):
        """
        Generate a tileset consisting of a single NUMPY tile.  Deposit it where the HTTP server can
        find the tileset, and fetch it.  Override the numpy image format such that the code thinks
        it does not need a seekable format.  This should trigger an exception on read.
        """
        image = slicedimage.TileSet(
            ["x", "y", "ch", "hyb"],
            {'ch': 1, 'hyb': 1},
            (100, 100),
        )

        tile = slicedimage.Tile(
            {
                'x': (0.0, 0.01),
                'y': (0.0, 0.01),
            },
            {
                'hyb': 0,
                'ch': 0,
            },
        )
        tile.numpy_array = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        image.add_tile(tile)

        partition_path = os.path.join(self.tempdir.name, "tileset.json")
        partition_doc = slicedimage.v0_0_0.Writer().generate_partition_document(
            image, partition_path)
        with open(partition_path, "w") as fh:
            json.dump(partition_doc, fh)

        try:
            slicedimage.ImageFormat.NUMPY._requires_seekable_file_handles = False
            result = slicedimage.Reader.parse_doc(
                "tileset.json",
                "http://localhost:{port}/".format(port=self.port))

            with self.assertRaises(IOError):
                list(result.tiles())[0].numpy_array
        finally:
            slicedimage.ImageFormat.NUMPY._requires_seekable_file_handles = True


if __name__ == "__main__":
    unittest.main()

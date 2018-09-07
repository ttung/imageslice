import hashlib
import json
import os
import sys
import time
import unittest

import numpy as np
import requests
import skimage.io
from requests import HTTPError

import slicedimage
from slicedimage.backends import ChecksumValidationError
from tests.utils import (
    build_skeleton_manifest,
    ContextualChildProcess,
    TemporaryDirectory,
    unused_tcp_port,
)


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
            "http://localhost:{port}/".format(port=self.port),
            allow_caching=False,
        )

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
            "http://localhost:{port}/".format(port=self.port),
            allow_caching=False,
        )

        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, tile.numpy_array))

    def test_checksum_good(self):
        self._test_checksum(True)

    def test_checksum_bad(self):
        self._test_checksum(False)

    def _test_checksum(self, good):
        """
        Generate a tileset consisting of a single TIFF tile.  If the parameter `good` is True, then
        we provide the correct checksum and verify loading works correctly.  Otherwise, we provide
        the incorrect checksum and verify that loading raises an exception.
        """
        # write the tiff file
        data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        file_path = os.path.join(self.tempdir.name, "tile.tiff")
        skimage.io.imsave(file_path, data, plugin="tifffile")
        if good:
            with open(file_path, "rb") as fh:
                checksum = hashlib.sha256(fh.read()).hexdigest()
        else:
            checksum = hashlib.sha256(b"not-empty-string").hexdigest()

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
        with open(os.path.join(self.tempdir.name, "tileset.json"), "w") as fh:
            fh.write(json.dumps(manifest))

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port),
            allow_caching=False,
        )

        if good:
            self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))
        else:
            with self.assertRaises(ChecksumValidationError):
                result.tiles()[0]._load()

    def test_error(self):
        """
        Verifies that we raise an exception when we fail to find a file.
        """
        with self.assertRaises(HTTPError):
            slicedimage.Reader.parse_doc(
                "tileset.json",
                "http://localhost:{port}/".format(port=self.port),
                allow_caching=False,
            )


if __name__ == "__main__":
    unittest.main()

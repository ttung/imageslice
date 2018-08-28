import hashlib
import json
import os
import sys
import time
import unittest

import numpy as np
import requests
import skimage.io
from six import unichr

import slicedimage
from slicedimage.backends import ChecksumValidationError
from tests.utils import (
    build_skeleton_manifest,
    ContextualChildProcess,
    TemporaryDirectory,
    unused_tcp_port,
)


class TestCachingBackend(unittest.TestCase):
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

    def test_cached_backend(self):
        """
        Generate a tileset consisting of a single TIFF tile.  Deposit it where the HTTP server can
        find the tileset, and fetch it. Then delete the TIFF file and re-run Reader.parse_doc with
        the same url and manifest to make sure we get the same results pulling the file
        from the cache
        """
        # write the tiff file
        data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        file_path = os.path.join(self.tempdir.name, "tile.tiff")
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
                "sha256": checksum
            },
        )
        with open(os.path.join(self.tempdir.name, "tileset.json"), "w") as fh:
            fh.write(json.dumps(manifest))

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))

        os.remove(os.path.join(self.tempdir.name, "tile.tiff"))
        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))

    def test_cache_pollution(self):
        """
        Generate a tileset consisting of a single TIFF tile.  Deposit it where the HTTP server can
        find the tileset, but corrupt the data before fetching it.  The fetch should fail.

        Return the data to an uncorrupted state and try to fetch it again.  It should not have
        cached the bad data.
        """
        # write the tiff file
        data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        file_path = os.path.join(self.tempdir.name, "tile.tiff")
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
                "sha256": checksum
            },
        )
        with open(os.path.join(self.tempdir.name, "tileset.json"), "w") as fh:
            fh.write(json.dumps(manifest))

        # corrupt the file
        with open(file_path, "r+b") as fh:
            fh.seek(0)
            real_first_byte = fh.read(1).decode("latin-1")
            fh.seek(0)
            fh.write(unichr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        with self.assertRaises(ChecksumValidationError):
            result.tiles()[0].numpy_array

        # un-corrupt the file
        with open(file_path, "r+b") as fh:
            fh.seek(0)
            real_first_byte = fh.read(1).decode("latin-1")
            fh.seek(0)
            fh.write(unichr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))

        result.tiles()[0].numpy_array


if __name__ == "__main__":
    unittest.main()

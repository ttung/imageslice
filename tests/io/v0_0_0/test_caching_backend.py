import contextlib
import json
import os
import random
import socket
import subprocess
import sys
import time
import unittest

import numpy as np
import requests
import skimage.io

import slicedimage

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from tests.utils import TemporaryDirectory


class TestCachingBackend(unittest.TestCase):
    def setUp(self, timeout_seconds=5):
        self.contexts = []
        self.tempdir = TemporaryDirectory()
        self.contexts.append(self.tempdir)
        self.port = _unused_tcp_port()

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
        find the tileset, and fetch it.
        """
        # write the tiff file
        data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
        skimage.io.imsave(os.path.join(self.tempdir.name, "tile.tiff"), data, plugin="tifffile")

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
                "sha256": random.getrandbits(128)
            },
        )
        with open(os.path.join(self.tempdir.name, "tileset.json"), "w") as fh:
            fh.write(json.dumps(manifest))
        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))
        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))
        # Now delete tile.tff from the http server and make sure Reader.parse_doc still works
        os.remove(os.path.join(self.tempdir.name, "tile.tiff"))
        result = slicedimage.Reader.parse_doc(
            "tileset.json",
            "http://localhost:{port}/".format(port=self.port))
        self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))


def _unused_tcp_port():
    """
    Return an unused TCP port.
    """
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class ContextualChildProcess(object):
    """
    Provides a context manager for wrapping a child process.
    """
    def __init__(self, *args, **kwargs):
        self.proc = subprocess.Popen(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.proc.terminate()
        self.proc.wait()


def build_skeleton_manifest():
    """
    Returns a 0.0.0 formatted manifest with no tiles.
    """
    return {
        "version": "0.0.0",
        "dimensions": [
            "x",
            "y",
            "hyb",
            "ch"
        ],
        "shape": {
            "hyb": 1,
            "ch": 1
        },
        "tiles": []
    }


if __name__ == "__main__":
    unittest.main()

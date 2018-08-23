import hashlib
import json
import os
import unittest

import numpy as np
import skimage.io

import slicedimage
from slicedimage.backends import ChecksumValidationError
from tests.utils import (
    build_skeleton_manifest,
    TemporaryDirectory,
)


class TestDiskBackend(unittest.TestCase):
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
        with TemporaryDirectory() as tempdir:
            data = np.random.randint(0, 65535, size=(100, 100), dtype=np.uint16)
            file_path = os.path.join(tempdir, "tile.tiff")
            skimage.io.imsave(file_path, data, plugin="tifffile")
            if good:
                with open(file_path, "rb") as fh:
                    checksum = hashlib.sha256(fh.read()).hexdigest()
            else:
                checksum = hashlib.sha256().hexdigest()

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

            result = slicedimage.Reader.parse_doc(
                "tileset.json",
                "file://{}".format(tempdir),
                allow_caching=False,
            )

            if good:
                self.assertTrue(np.array_equal(list(result.tiles())[0].numpy_array, data))
            else:
                with self.assertRaises(ChecksumValidationError):
                    result.tiles()[0]._load()


if __name__ == "__main__":
    unittest.main()

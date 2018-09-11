import collections
import os
import pytest
import unittest

import slicedimage


baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestValidate(unittest.TestCase):

    def test_checksums_good(self):
        result = slicedimage.Reader.parse_doc("hybridization-fov_000.json", baseurl)
        self.assertIsInstance(result, slicedimage.TileSet)
        self.assertEqual(result.shape, {'c': 1, 'r': 1, 'z': 1})
        result.validate()

    def test_checksums_bad(self):
        result = slicedimage.Reader.parse_doc("hybridization-fov_000.broken", baseurl)
        self.assertIsInstance(result, slicedimage.TileSet)
        self.assertEqual(result.shape, {'c': 1, 'r': 1, 'z': 1})
        # FIXME: backend is complaining on _load before we get to the assert
        with pytest.raises(slicedimage.backends._base.ChecksumValidationError):
            result.validate()

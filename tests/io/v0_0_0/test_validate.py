import collections
import os
import unittest

import slicedimage


baseurl = "file://{}".format(os.path.abspath(os.path.dirname(__file__)))


class TestValidate(unittest.TestCase):
    def test_checksums(self):
        result = slicedimage.Reader.parse_doc("hybridization-fov_000.json", baseurl)
        self.assertIsInstance(result, slicedimage.TileSet)
        self.assertEqual(result.shape, {'c': 1, 'r': 1, 'z': 1})
        result.validate()

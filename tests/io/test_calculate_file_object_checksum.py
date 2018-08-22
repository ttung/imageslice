import hashlib
import unittest
from io import IOBase, BytesIO

from slicedimage.backends._base import CalculateFileObjectChecksum


class TestCalculateFileObjectChecksum(unittest.TestCase):
    def test_instanceof(self, test_inp=b"abcde"):
        obj = BytesIO(test_inp)
        with CalculateFileObjectChecksum(obj, None) as fh:
            self.assertIsInstance(fh, IOBase)

    def test_read(self, test_inp=b"abcde"):
        obj = BytesIO(test_inp)
        with CalculateFileObjectChecksum(obj, None) as fh:
            self.assertEqual(fh.read(2), b"ab")
            self.assertEqual(fh.read(1), b"c")
            self.assertEqual(fh.read(), b"de")

    def test_checksum_read(self, test_inp=b"abcde"):
        obj = BytesIO(test_inp)
        hasher = hashlib.sha256()
        hasher.update(test_inp)
        expected_sha256 = hasher.hexdigest()

        with CalculateFileObjectChecksum(obj, expected_sha256) as fh:
            self.assertEqual(fh.read(2), b"ab")
            self.assertEqual(fh.read(1), b"c")
            self.assertEqual(fh.read(), b"de")

    def test_checksum_mismatch(self, test_inp=b"abcde"):
        obj = BytesIO(test_inp)

        with self.assertRaises(ValueError):
            with CalculateFileObjectChecksum(obj, "not-the-right-checksum") as fh:
                fh.read(5)

    def test_checksum_incomplete_read(self, test_inp=b"abcde"):
        obj = BytesIO(test_inp)
        hasher = hashlib.sha256()
        hasher.update(test_inp)
        expected_sha256 = hasher.hexdigest()

        with CalculateFileObjectChecksum(obj, expected_sha256) as fh:
            fh.read(3)


if __name__ == "__main__":
    unittest.main()

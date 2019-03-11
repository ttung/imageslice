import contextlib
import hashlib
import os
import tempfile
import unittest

from slicedimage.backends import ChecksumValidationError, DiskBackend


class TestDiskBackend(unittest.TestCase):
    def test_checksum_good(self):
        with self._test_checksum_setup() as setupdata:
            filepath, data, expected_checksum = setupdata

            backend = DiskBackend(os.path.dirname(filepath))
            with backend.read_contextmanager(os.path.basename(filepath), expected_checksum) as cm:
                self.assertEqual(cm.read(), data)

    def test_checksum_bad(self):
        with self._test_checksum_setup() as setupdata:
            filepath, data, expected_checksum = setupdata

            # make the hash incorrect
            expected_checksum = "{:x}".format(int(hashlib.sha256().hexdigest(), 16) + 1)

            backend = DiskBackend(os.path.dirname(filepath))
            with self.assertRaises(ChecksumValidationError):
                with backend.read_contextmanager(
                        os.path.basename(filepath),
                        expected_checksum) as cm:
                    self.assertEqual(cm.read(), data)

    def test_reentrant(self):
        with self._test_checksum_setup() as setupdata:
            filepath, data, expected_checksum = setupdata

            backend = DiskBackend(os.path.dirname(filepath))
            with backend.read_contextmanager(os.path.basename(filepath), expected_checksum) as cm0:
                data0 = cm0.read(1)
                with backend.read_contextmanager(
                        os.path.basename(filepath),
                        expected_checksum) as cm1:
                    data1 = cm1.read()

                data0 = data0 + cm0.read()

                self.assertEqual(data, data0)
                self.assertEqual(data, data1)

    @staticmethod
    @contextlib.contextmanager
    def _test_checksum_setup():
        """
        Write some random data to a temporary file and yield its path, the data, and the checksum of
        the data.
        """
        # write the file
        data = os.urandom(1024)

        expected_checksum = hashlib.sha256(data).hexdigest()

        with tempfile.NamedTemporaryFile() as tfh:
            tfh.write(data)
            tfh.flush()

            yield tfh.name, data, expected_checksum


if __name__ == "__main__":
    unittest.main()

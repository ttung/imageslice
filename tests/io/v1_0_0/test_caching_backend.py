import contextlib
import hashlib
import os
import sys
import tempfile
import time
import unittest

import requests
from six import unichr

from slicedimage.backends import ChecksumValidationError, HttpBackend, CachingBackend
from tests.utils import (
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

        self.cachedir = TemporaryDirectory()
        self.contexts.append(self.cachedir)

        self.http_backend = HttpBackend("http://0.0.0.0:{port}".format(port=self.port))
        self.caching_backend = CachingBackend(self.cachedir.name, self.http_backend)

    def tearDown(self):
        for context in self.contexts:
            context.__exit__(*sys.exc_info())

    def test_checksum_good(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                self.assertEqual(cm.read(), data)

    def test_checksum_bad(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            # make the hash incorrect
            expected_checksum = "{:x}".format(int(hashlib.sha256().hexdigest(), 16) + 1)

            with self.assertRaises(ChecksumValidationError):
                with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                    self.assertEqual(cm.read(), data)

    def test_cache_pollution(self):
        """
        Try to fetch a file but corrupt the data before fetching it.  The fetch should fail.

        Return the data to an uncorrupted state and try to fetch it again.  It should not have
        cached the bad data.
        """
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            # corrupt the file
            with open(os.path.join(self.tempdir.name, filename), "r+b") as fh:
                fh.seek(0)
                real_first_byte = fh.read(1).decode("latin-1")
                fh.seek(0)
                fh.write(unichr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

            with self.assertRaises(ChecksumValidationError):
                with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                    self.assertEqual(cm.read(), data)

            # un-corrupt the file
            with open(os.path.join(self.tempdir.name, filename), "r+b") as fh:
                fh.seek(0)
                real_first_byte = fh.read(1).decode("latin-1")
                fh.seek(0)
                fh.write(unichr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

            with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                self.assertEqual(cm.read(), data)

    def test_reentrant(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm0:
                data0 = cm0.read(1)
                with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm1:
                    data1 = cm1.read()

                data0 = data0 + cm0.read()

                self.assertEqual(data, data0)
                self.assertEqual(data, data1)

    @staticmethod
    @contextlib.contextmanager
    def _test_checksum_setup(tempdir):
        """
        Write some random data to a temporary file and yield its path, the data, and the checksum of
        the data.
        """
        # write the file
        data = os.urandom(1024)

        expected_checksum = hashlib.sha256(data).hexdigest()

        with tempfile.NamedTemporaryFile(dir=tempdir) as tfh:
            tfh.write(data)
            tfh.flush()

            yield os.path.basename(tfh.name), data, expected_checksum


if __name__ == "__main__":
    unittest.main()

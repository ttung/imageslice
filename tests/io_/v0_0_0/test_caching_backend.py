import contextlib
import hashlib
import os
import sys
import tempfile
import time
import unittest

import requests

from slicedimage.backends import ChecksumValidationError, HttpBackend
from tests.utils import (
    ContextualCachingBackend,
    ContextualChildProcess,
    unused_tcp_port,
)


class TestCachingBackend(unittest.TestCase):
    def setUp(self, timeout_seconds=5):
        self.contexts = []
        self.tempdir = tempfile.TemporaryDirectory()
        self.contexts.append(self.tempdir)
        self.port = unused_tcp_port()

        self.contexts.append(ContextualChildProcess(
            [
                "python",
                "-m",
                "http.server",
                str(self.port),
                "--bind",
                "127.0.0.1",
            ],
            cwd=self.tempdir.name,
        ).__enter__())

        end = time.time() + timeout_seconds
        while True:
            try:
                requests.get("http://127.0.0.1:{port}".format(port=self.port))
                break
            except requests.ConnectionError:
                if time.time() > end:
                    raise

        self.cachedir = tempfile.TemporaryDirectory()
        self.contexts.append(self.cachedir)

        self.http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=self.port))
        caching_context = ContextualCachingBackend(self.cachedir.name, self.http_backend)
        self.caching_backend = caching_context.__enter__()
        self.contexts.append(caching_context)

    def tearDown(self):
        for context in reversed(self.contexts):
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
                fh.write(chr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

            with self.assertRaises(ChecksumValidationError):
                with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                    self.assertEqual(cm.read(), data)

            # un-corrupt the file
            with open(os.path.join(self.tempdir.name, filename), "r+b") as fh:
                fh.seek(0)
                real_first_byte = fh.read(1).decode("latin-1")
                fh.seek(0)
                fh.write(chr(ord(real_first_byte) ^ 0xff).encode("latin-1"))

            with self.caching_backend.read_contextmanager(filename, expected_checksum) as cm:
                self.assertEqual(cm.read(), data)

    def test_reentrant(self):
        if os.name == "nt":
            self.skipTest("Cannot run reentrant test on Windows")
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

        with tempfile.NamedTemporaryFile(dir=tempdir, delete=False) as tfh:
            tfh.write(data)

        yield os.path.basename(tfh.name), data, expected_checksum


if __name__ == "__main__":
    unittest.main()

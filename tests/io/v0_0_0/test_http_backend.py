import contextlib
import hashlib
import os
import sys
import tempfile
import time
import unittest

import requests
from requests import HTTPError

from slicedimage.backends import ChecksumValidationError, HttpBackend
from tests.utils import (
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

        self.http_backend = HttpBackend("http://0.0.0.0:{port}".format(port=self.port))

    def tearDown(self):
        for context in self.contexts:
            context.__exit__(*sys.exc_info())

    def test_checksum_good(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            with self.http_backend.read_contextmanager(filename, expected_checksum) as cm:
                self.assertEqual(cm.read(), data)

    def test_checksum_bad(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            # make the hash incorrect
            expected_checksum = "{:x}".format(int(hashlib.sha256().hexdigest(), 16) + 1)

            with self.assertRaises(ChecksumValidationError):
                with self.http_backend.read_contextmanager(filename, expected_checksum) as cm:
                    self.assertEqual(cm.read(), data)

    def test_reentrant(self):
        with self._test_checksum_setup(self.tempdir.name) as setupdata:
            filename, data, expected_checksum = setupdata

            with self.http_backend.read_contextmanager(filename, expected_checksum) as cm0:
                data0 = cm0.read(1)
                with self.http_backend.read_contextmanager(filename, expected_checksum) as cm1:
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

    def test_error(self):
        """
        Verifies that we raise an exception when we fail to find a file.
        """
        with self.assertRaises(HTTPError):
            backend = HttpBackend("http://0.0.0.0:{port}".format(port=self.port))
            with self.assertRaises(ChecksumValidationError):
                with backend.read_contextmanager("tileset.json") as cm:
                    cm.read()


if __name__ == "__main__":
    unittest.main()

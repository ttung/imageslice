import contextlib
import hashlib
import os
import tempfile
import threading
import time

import pytest
import requests
from requests import HTTPError

from slicedimage.backends import ChecksumValidationError, HttpBackend
from slicedimage.backends import _http
from tests.utils import (
    ContextualChildProcess,
    unused_tcp_port,
)


@pytest.fixture(scope="module")
def http_server(timeout_seconds=5):
    with tempfile.  TemporaryDirectory() as tempdir:

        port = unused_tcp_port()

        with ContextualChildProcess(
                [
                    "python",
                    "-m",
                    "http.server",
                    str(port),
                    "--bind",
                    "127.0.0.1",
                ],
                cwd=tempdir,
        ):
            end = time.time() + timeout_seconds

            while True:
                try:
                    requests.get("http://127.0.0.1:{port}".format(port=port))
                    break
                except requests.ConnectionError:
                    if time.time() > end:
                        raise

            yield tempdir, port


def test_checksum_good(http_server):
    tempdir, port = http_server
    http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=port))
    with _test_checksum_setup(tempdir) as setupdata:
        filename, data, expected_checksum = setupdata

        with http_backend.read_contextmanager(filename, expected_checksum) as cm:
            assert cm.read() == data


def test_checksum_bad(http_server):
    tempdir, port = http_server
    http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=port))
    with _test_checksum_setup(tempdir) as setupdata:
        filename, data, expected_checksum = setupdata

        # make the hash incorrect
        expected_checksum = "{:x}".format(int(hashlib.sha256().hexdigest(), 16) + 1)

        with pytest.raises(ChecksumValidationError):
            with http_backend.read_contextmanager(filename, expected_checksum) as cm:
                assert cm.read() == data


def test_reentrant(http_server):
    tempdir, port = http_server
    http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=port))
    with _test_checksum_setup(tempdir) as setupdata:
        filename, data, expected_checksum = setupdata

        with http_backend.read_contextmanager(filename, expected_checksum) as cm0:
            data0 = cm0.read(1)
            with http_backend.read_contextmanager(filename, expected_checksum) as cm1:
                data1 = cm1.read()

            data0 = data0 + cm0.read()

            assert data == data0
            assert data == data1


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


def test_error(http_server):
    """
    Verifies that we raise an exception when we fail to find a file.
    """
    tempdir, port = http_server
    http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=port))
    with pytest.raises(HTTPError):
        with pytest.raises(ChecksumValidationError):
            with http_backend.read_contextmanager("tileset.json") as cm:
                cm.read()


def test_retry(monkeypatch, http_server):
    """
    Verifies that the retry logic is reasonable.  Since we normally only retry on http connectivity
    issues, or 50x errors, we monkeypatch the list of HTTP status codes we retry on to {404}, and
    induce a 404 error.  We also start a thread that creates the file we are looking for.

    Then we attempt to fetch the file.  It should fail a few times, and then successfully return the
    file.
    """
    tempdir, port = http_server
    http_backend = HttpBackend("http://127.0.0.1:{port}".format(port=port))

    def sleep_and_make_file():
        time.sleep(5.0)
        data = os.urandom(1024)
        with open(os.path.join(tempdir, "tileset.json"), "w") as fh:
            fh.write(data)
            fh.flush()

    thread = threading.Thread(target=sleep_and_make_file)
    thread.setDaemon(True)
    thread.start()

    with monkeypatch.context() as mc:
        mc.setattr(_http, "RETRY_STATUS_CODES", frozenset({404}))
        with http_backend.read_contextmanager("tileset.json") as cm:
            cm.read()

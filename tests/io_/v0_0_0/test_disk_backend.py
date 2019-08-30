import contextlib
import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from slicedimage._compat import fspath
from slicedimage.backends import ChecksumValidationError, DiskBackend


def test_checksum_good(tmpdir):
    with _test_checksum_setup(tmpdir) as setupdata:
        filepath, data, expected_checksum = setupdata

        backend = DiskBackend(os.path.dirname(filepath))
        with backend.read_contextmanager(os.path.basename(filepath), expected_checksum) as cm:
            assert cm.read() == data


def test_checksum_bad(tmpdir):
    with _test_checksum_setup(tmpdir) as setupdata:
        filepath, data, expected_checksum = setupdata

        # make the hash incorrect
        expected_checksum = "{:x}".format(int(hashlib.sha256().hexdigest(), 16) + 1)

        backend = DiskBackend(os.path.dirname(filepath))
        with pytest.raises(ChecksumValidationError):
            with backend.read_contextmanager(
                    os.path.basename(filepath),
                    expected_checksum) as cm:
                assert cm.read() == data


def test_reentrant(tmpdir):
    with _test_checksum_setup(tmpdir) as setupdata:
        filepath, data, expected_checksum = setupdata

        backend = DiskBackend(os.path.dirname(filepath))
        with backend.read_contextmanager(os.path.basename(filepath), expected_checksum) as cm0:
            data0 = cm0.read(1)
            with backend.read_contextmanager(
                    os.path.basename(filepath),
                    expected_checksum) as cm1:
                data1 = cm1.read()

            data0 = data0 + cm0.read()

            assert data == data0
            assert data == data1


@contextlib.contextmanager
def _test_checksum_setup(tmpdir: Path):
    """
    Write some random data to a temporary file and yield its path, the data, and the checksum of
    the data.
    """
    # write the file
    data = os.urandom(1024)

    expected_checksum = hashlib.sha256(data).hexdigest()

    with tempfile.NamedTemporaryFile(dir=fspath(tmpdir), delete=False) as tfh:
        tfh.write(data)

    yield tfh.name, data, expected_checksum

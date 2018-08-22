from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import io


class Backend(object):
    def read_contextmanager(self, name, checksum_sha256=None, seekable=False):
        raise NotImplementedError()

    def write_file_handle(self, name):
        raise NotImplementedError()

    def write_file_from_handle(self, name, source_handle, block_size=(128 * 1024)):
        with self.write_file_handle(name) as dest_handle:
            data = source_handle.read(block_size)
            if len(data) == 0:
                return
            dest_handle.write(data)


class ChecksumValidationError(ValueError):
    """Raised when the downloaded file does not match the expected checksum."""
    pass


class CalculateFileObjectChecksum(object):
    """
    Context manager that wraps another context manager that returns a readable file handle.
    `CalculateFileObjectChecksum` will wrap the returned readable file handle such that a sha256
    checksum is calculated against the data read.  If the file is not read to completion by the time
    the context manager exits, it is read to completion so that the entire file's contents is
    checksummed.

    If the checksum does not match the expected sha256, raise ChecksumValidationError.
    """
    def __init__(self, wrapped_file_contextmanager, expected_sha256_checksum):
        self._wrapped_file_contextmanager = wrapped_file_contextmanager
        self._io = None
        self._checksummer = hashlib.sha256()
        self._expected_sha256_checksum = expected_sha256_checksum

    def __enter__(self):
        if self._expected_sha256_checksum is None:
            self._io = self._wrapped_file_contextmanager.__enter__()
        else:
            self._io = _ChecksummingFile(
                self._wrapped_file_contextmanager.__enter__(), self._checksummer)
        return self._io

    def __exit__(self, exc_type, exc_val, exc_tb):
        # finish reading the data.
        self._io.read()
        calculated_checksum = self._checksummer.hexdigest()
        if (self._expected_sha256_checksum is not None and
                calculated_checksum != self._expected_sha256_checksum):
            raise ChecksumValidationError(
                "calculated checksum ({}) does not match expected checksum ({})".format(
                    calculated_checksum, self._expected_sha256_checksum))

        return self._wrapped_file_contextmanager.__exit__(exc_type, exc_val, exc_tb)


class _ChecksummingFile(io.IOBase):
    """
    Read-only file-like handle that delegates read calls to a wrapped file-like handle.  As the file
    is read, a checksum is calculated on the data read.
    """
    def __init__(self, wrapped_io, checksummer):
        self._wrapped_io = wrapped_io
        self._checksummer = checksummer

    def read(self, size=-1):
        data = self._wrapped_io.read(size)
        self._checksummer.update(data)
        return data

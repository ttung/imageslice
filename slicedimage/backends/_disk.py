from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import os

from ._base import Backend, ChecksumValidationError


class DiskBackend(Backend):
    def __init__(self, basedir):
        self._basedir = basedir

    def read_contextmanager(self, name, checksum_sha256=None, seekable=False):
        return _FileLikeContextManager(os.path.join(self._basedir, name), checksum_sha256)

    def write_file_handle(self, name=None):
        return open(os.path.join(self._basedir, name), "wb")


class _FileLikeContextManager(object):
    def __init__(self, path, checksum_sha256, read_chunk_size=1024 * 1024):
        self.path = path
        self.checksum_sha256 = checksum_sha256
        self.handle = None
        self.read_chunk_size = read_chunk_size

    def __enter__(self):
        self.handle = open(self.path, "rb")
        if self.checksum_sha256 is not None:
            hasher = hashlib.sha256()
            # calculate the checksum.  we don't use CalculateFileObjectChecksum because the
            # file-like handle returned by DiskBackend supports seek operations.
            while True:
                data = self.handle.read(self.read_chunk_size)
                if len(data) == 0:
                    break
                hasher.update(data)
            calculated_checksum = hasher.hexdigest()
            if calculated_checksum != self.checksum_sha256:
                raise ChecksumValidationError(
                    "calculated checksum ({}) does not match expected checksum ({})".format(
                        calculated_checksum, self.checksum_sha256))
            self.handle.seek(0)
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handle is not None:
            return self.handle.__exit__(exc_type, exc_val, exc_tb)

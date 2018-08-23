from __future__ import absolute_import, division, print_function, unicode_literals

import os

from ._base import Backend, verify_checksum


class DiskBackend(Backend):
    def __init__(self, basedir):
        self._basedir = basedir

    def read_contextmanager(self, name, checksum_sha256=None):
        return _FileLikeContextManager(os.path.join(self._basedir, name), checksum_sha256)

    def write_file_handle(self, name=None):
        return open(os.path.join(self._basedir, name), "wb")


class _FileLikeContextManager(object):
    def __init__(self, path, checksum_sha256):
        self.path = path
        self.checksum_sha256 = checksum_sha256
        self.handle = None

    def __enter__(self):
        self.handle = open(self.path, "rb")
        verify_checksum(self.handle, self.checksum_sha256)
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handle is not None:
            return self.handle.__exit__(exc_type, exc_val, exc_tb)

from __future__ import absolute_import, division, print_function, unicode_literals

import io

from diskcache import Cache

from ._base import Backend

size_limit = 5e9


class CachingBackend(Backend):

    def __init__(self, cacheroot, authoritative_backend):
        self._cacheroot = cacheroot
        self._authoritative_backend = authoritative_backend
        self.cache = Cache(cacheroot, size_limit=int(size_limit))

    def read_file_handle_callable(self, name, checksum_sha256=None, seekable=False):
        def returned_callable():
            if checksum_sha256:
                if checksum_sha256 not in self.cache:
                    sfh = self._authoritative_backend.read_file_handle(name)
                    self.cache.set(checksum_sha256, sfh.read())
                file_data = self.cache.read(checksum_sha256)
                # If the data is small enough, the DiskCache library returns the cache data
                # as bytes instead of a buffered reader.
                # In that case, we want to wrap it in a file-like object.
                if isinstance(file_data, io.IOBase):
                    return file_data
                return io.BytesIO(file_data)
            else:
                return self._authoritative_backend.read_file_handle(name)
        return returned_callable

    def write_file_handle(self, name):
        return self._authoritative_backend.write_file_handle(name)

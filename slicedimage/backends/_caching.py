from __future__ import absolute_import, division, print_function, unicode_literals

import io

from diskcache import Cache
from io import BytesIO

from ._base import Backend


class CachingBackend(Backend):
    def __init__(self, cacheroot, authoritative_backend):
        self._cacheroot = cacheroot
        self._authoritative_backend = authoritative_backend
        self.cache = Cache(cacheroot, size_limit=int(5e9))

    def read_file_handle_callable(self, name, checksum_sha1=None, seekable=False):
        def returned_callable():
            if checksum_sha1:
                if not self.cache.get(checksum_sha1):
                    sfh = self._authoritative_backend.read_file_handle(name)
                    self.cache.set(checksum_sha1, sfh.data)
                file_data = self.cache.read(checksum_sha1)
                # The DiskCache library returns the cache data as bytes instead of a buffered reader
                # If the data is small enough check what was returned and convert to a reader
                if isinstance(file_data, io.IOBase):
                    return file_data
                return BytesIO(file_data)
            else:
                return self._authoritative_backend.read_file_handle(name)
        return returned_callable

    def write_file_handle(self, name):
        return self._authoritative_backend.write_file_handle(name)

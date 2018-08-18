from __future__ import absolute_import, division, print_function, unicode_literals

import io

from diskcache import Cache

from ._base import Backend

SIZE_LIMIT = 5e9


class CachingBackend(Backend):

    def __init__(self, cacheroot, authoritative_backend):
        self._cacheroot = cacheroot
        self._authoritative_backend = authoritative_backend
        self.cache = Cache(cacheroot, size_limit=int(SIZE_LIMIT))

    def read_file_handle_callable(self, name, checksum_sha256=None, seekable=False):
        def returned_callable():
            if checksum_sha256:
                try:
                    file_data = self.cache.read(checksum_sha256)
                except KeyError:
                    # not in cache :(
                    sfh = self._authoritative_backend.read_file_handle(name)
                    file_data = sfh.read()
                    self.cache.set(checksum_sha256, file_data)
                    return io.BytesIO(file_data)
                else:
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

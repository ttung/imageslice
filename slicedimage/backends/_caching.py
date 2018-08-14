from __future__ import absolute_import, division, print_function, unicode_literals
from diskcache import Cache

from slicedimage.backends._http import _BytesIOContextManager
from ._base import Backend


class CachingBackend(Backend):
    def __init__(self, cacheroot, authoritative_backend):
        self._cacheroot = cacheroot
        self._authoritative_backend = authoritative_backend
        self.cache = Cache(cacheroot, size_limit=int(4e9))


    def read_file_handle_callable(self, name, checksum_sha1=None, seekable=False):
        def returned_callable():
            #only need to cache tile data?
            if checksum_sha1:
                if not self.cache.get(checksum_sha1):
                    sfh = self._authoritative_backend.read_file_handle(name, checksum_sha1)
                    while True:
                        data = sfh.read(128 * 1024)
                        if len(data) == 0:
                            break
                        self.cache.set(checksum_sha1, data, read=True)
                return _BytesIOContextManager(self.cache.get(checksum_sha1))
            else:
                return self._authoritative_backend.read_file_handle(name)
        return returned_callable

    def write_file_handle(self, name):
        return self._authoritative_backend.write_file_handle(name)



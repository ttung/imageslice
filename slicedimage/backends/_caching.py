from __future__ import absolute_import, division, print_function, unicode_literals

import io
from threading import Lock

from diskcache import Cache

from ._base import Backend, verify_checksum

SIZE_LIMIT = 5e9
CACHE_VERSION = "v1"


class CachingBackend(Backend):
    _LOCK = Lock()
    _CACHE = {}

    def __init__(self, cacheroot, authoritative_backend, size_limit=SIZE_LIMIT):
        with CachingBackend._LOCK:
            if cacheroot not in CachingBackend._CACHE:
                CachingBackend._CACHE[cacheroot] = Cache(cacheroot, size_limit=int(size_limit))
            self._cache = CachingBackend._CACHE[cacheroot]
        self._authoritative_backend = authoritative_backend

    def read_contextmanager(self, name, checksum_sha256=None):
        if checksum_sha256 is not None:
            return _CachingBackendContextManager(
                self._authoritative_backend, self._cache, name, checksum_sha256)
        else:
            return self._authoritative_backend.read_contextmanager(
                name, checksum_sha256)

    def write_file_handle(self, name):
        return self._authoritative_backend.write_file_handle(name)


class _CachingBackendContextManager(object):
    def __init__(self, authoritative_backend, cache, name, checksum_sha256):
        self.authoritative_backend = authoritative_backend
        self.cache = cache
        self.name = name
        self.checksum_sha256 = checksum_sha256
        self.handle = None

    def __enter__(self):
        cache_key = "{}-{}".format(CACHE_VERSION, self.checksum_sha256)
        try:
            file_data = self.cache.read(cache_key)
        except KeyError:
            # not in cache :(
            with self.authoritative_backend.read_contextmanager(
                    self.name, self.checksum_sha256) as sfh:
                file_data = sfh.read()
            self.cache.set(cache_key, file_data)
            self.handle = io.BytesIO(file_data)

            # we are directly returning the data from the authoritative backend, which we assume
            # is verifying the checksum, so we don't layer on another checksum calculation.
        else:
            # If the data is small enough, the DiskCache library returns the cache data
            # as bytes instead of a buffered reader.
            # In that case, we want to wrap it in a file-like object.
            if isinstance(file_data, io.IOBase):
                self.handle = file_data
            else:
                self.handle = io.BytesIO(file_data)
            verify_checksum(self.handle, self.checksum_sha256)

        return self.handle.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handle is not None:
            return self.handle.__exit__(exc_type, exc_val, exc_tb)

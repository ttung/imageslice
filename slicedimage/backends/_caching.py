from __future__ import absolute_import, division, print_function, unicode_literals

import os

from ._base import Backend


class CachingBackend(Backend):
    def __init__(self, cacheroot, authoritative_backend):
        self._cacheroot = cacheroot
        self._authoritative_backend = authoritative_backend

    def read_file_handle_callable(self, name, checksum_sha1=None):
        # TODO: (ttung) This is a very very primitive cache.  Should make this more robust with evictions and all that
        # good stuff.
        cachedir = os.path.join(self._cacheroot, checksum_sha1[0:2], checksum_sha1[2:4])
        cachepath = os.path.join(cachedir, checksum_sha1)
        if not os.path.exists(cachepath):
            os.makedirs(cachedir)
            with open(cachepath, "w") as dfh, self._authoritative_backend.read_file_handle(name, checksum_sha1) as sfh:
                while True:
                    data = sfh.read(128 * 1024)
                    if len(data) == 0:
                        break
                    dfh.write(data)

        return lambda: open(cachepath, "r")

    def write_file_handle(self, name):
        return self._authoritative_backend.write_file_handle(name)

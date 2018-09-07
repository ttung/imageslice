from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from io import BytesIO

from slicedimage.urlpath import pathjoin
from ._base import Backend, verify_checksum


class HttpBackend(Backend):
    def __init__(self, baseurl):
        self._baseurl = baseurl

    def read_contextmanager(self, name, checksum_sha256=None):
        parsed = pathjoin(self._baseurl, name)
        return _UrlContextManager(parsed, checksum_sha256)


class _UrlContextManager(object):
    def __init__(self, url, checksum_sha256):
        self.url = url
        self.checksum_sha256 = checksum_sha256
        self.handle = None

    def __enter__(self):
        resp = requests.get(self.url)
        resp.raise_for_status()
        self.handle = BytesIO(resp.content)
        verify_checksum(self.handle, self.checksum_sha256)
        return self.handle.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.handle.__exit__(exc_type, exc_val, exc_tb)

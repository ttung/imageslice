from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from io import BytesIO

from slicedimage.urlpath import pathjoin
from ._base import Backend


class HttpBackend(Backend):
    def __init__(self, baseurl):
        self._baseurl = baseurl

    def read_contextmanager(self, name, checksum_sha256=None, seekable=False):
        parsed = pathjoin(self._baseurl, name)
        return _UrlContextManager(parsed, checksum_sha256, seekable)


class _UrlContextManager(object):
    def __init__(self, url, checksum_sha256, seekable):
        self.url = url
        self.checksum_sha256 = checksum_sha256
        self.seekable = seekable
        self.handle = None

    def __enter__(self):
        if self.seekable:
            req = requests.get(self.url)
            self.handle = BytesIO(req.content)
        else:
            req = requests.get(self.url, stream=True)
            self.handle = req.raw
        return self.handle.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handle is not None:
            return self.handle.__exit__(exc_type, exc_val, exc_tb)

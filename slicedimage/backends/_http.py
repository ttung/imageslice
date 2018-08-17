from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from six import BytesIO

from slicedimage.urlpath import pathjoin
from ._base import Backend


class _BytesIOContextManager(BytesIO):
    """Extension to BytesIO, but supports acting like a context manager."""
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class HttpBackend(Backend):
    def __init__(self, baseurl):
        self._baseurl = baseurl

    def read_file_handle_callable(self, name, checksum_sha256=None, seekable=False):
        def returned_callable():
            parsed = pathjoin(self._baseurl, name)
            if seekable:
                req = requests.get(parsed)
                return _BytesIOContextManager(req.content)
            req = requests.get(parsed, stream=True)
            return req.raw
        return returned_callable

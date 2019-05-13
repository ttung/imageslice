from __future__ import absolute_import, division, print_function, unicode_literals

import requests
from io import BytesIO

from requests.adapters import HTTPAdapter
from urllib3.util import retry

from slicedimage.urlpath import pathjoin
from ._base import Backend, verify_checksum


RETRY_STATUS_CODES = frozenset({500, 502, 503, 504})


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
        session = requests.Session()
        retry_policy = retry.Retry(
            connect=10, read=10, status=10, backoff_factor=0.1, status_forcelist=RETRY_STATUS_CODES)
        adapter = HTTPAdapter(max_retries=retry_policy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        resp = session.get(self.url)
        resp.raise_for_status()
        self.handle = BytesIO(resp.content)
        verify_checksum(self.handle, self.checksum_sha256)
        return self.handle.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.handle.__exit__(exc_type, exc_val, exc_tb)

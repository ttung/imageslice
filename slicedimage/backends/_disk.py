from __future__ import absolute_import, division, print_function, unicode_literals

import os

from ._base import Backend


class DiskBackend(Backend):
    def __init__(self, basedir):
        self._basedir = basedir

    def read_file_handle_callable(self, name, checksum_sha1=None):
        return lambda: open(os.path.join(self._basedir, name), "rb")

    def write_file_handle(self, name=None):
        return open(os.path.join(self._basedir, name), "wb")

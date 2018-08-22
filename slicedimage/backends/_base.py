from __future__ import absolute_import, division, print_function, unicode_literals


class Backend(object):
    def read_contextmanager(self, name, checksum_sha256=None, seekable=False):
        raise NotImplementedError()

    def write_file_handle(self, name):
        raise NotImplementedError()

    def write_file_from_handle(self, name, source_handle, block_size=(128 * 1024)):
        with self.write_file_handle(name) as dest_handle:
            data = source_handle.read(block_size)
            if len(data) == 0:
                return
            dest_handle.write(data)


class FileNotFoundError(Exception):
    pass

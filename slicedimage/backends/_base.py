from __future__ import absolute_import, division, print_function, unicode_literals


class Backend(object):
    def read_file_handle_callable(self, name, checksum_sha1=None):
        raise NotImplementedError()

    def read_file_handle(self, name, checksum_sha1=None):
        return self.read_file_handle_callable(name, checksum_sha1)()

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

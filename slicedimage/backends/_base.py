from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib


class Backend(object):
    def read_contextmanager(self, name, checksum_sha256=None):
        raise NotImplementedError()

    def write_file_handle(self, name):
        raise NotImplementedError()

    def write_file_from_handle(self, name, source_handle, block_size=(128 * 1024)):
        with self.write_file_handle(name) as dest_handle:
            data = source_handle.read(block_size)
            if len(data) == 0:
                return
            dest_handle.write(data)


class ChecksumValidationError(ValueError):
    """Raised when the downloaded file does not match the expected checksum."""
    pass


def verify_checksum(fh, expected_sha256_checksum, block_size=1024 * 1024):
    """
    Given a file-like handle, read from it in chunks to verify that the sha256 checksum matches
    `expected_sha256_checksum`.  If the checksum does not match, raise `ChecksumValidationError`.

    Before returning, the file handle is reset to the start of the file.
    :param fh: The file-like handle.
    :param expected_sha256_checksum: The expected sha256 checksum in hex.  If this parameter is
                                     None, then the method immediately returns.
    :param block_size: The block size of the IO.
    """
    if expected_sha256_checksum is None:
        return

    checksummer = hashlib.sha256()

    assert fh.tell() == 0
    while True:
        data = fh.read(block_size)
        checksummer.update(data)
        if len(data) == 0:
            calculated_checksum = checksummer.hexdigest()
            if calculated_checksum != expected_sha256_checksum:
                raise ChecksumValidationError(
                    "calculated checksum ({}) does not match expected checksum ({})".format(
                        calculated_checksum, expected_sha256_checksum))
            break

    fh.seek(0)

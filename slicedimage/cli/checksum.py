from __future__ import absolute_import, division, print_function, unicode_literals

from slicedimage import Reader, Writer
from slicedimage.io import resolve_path_or_url
from ._base import CliCommand


class ChecksumCommand(CliCommand):
    @classmethod
    def register_parser(cls, subparser_root):
        checksum_command = subparser_root.add_parser(
            "checksum",
            help="Read a partition file and add missing checksums.")
        checksum_command.add_argument(
            "in_url",
            help="URL for the source partition file")
        checksum_command.add_argument(
            "out_path",
            help="Path to write partition file with checksums")
        checksum_command.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty-print the output file")

        return checksum_command

    @classmethod
    def run_command(cls, args):
        _, name, baseurl = resolve_path_or_url(args.in_url)
        slicedimage = Reader.parse_doc(name, baseurl)

        Writer.write_to_path(
            slicedimage,
            args.out_path,
            pretty=args.pretty,
            tile_opener=fake_file_opener,
            tile_writer=identity_writer)


def fake_file_opener(partition_path, tile, ext):
    class null_file_handle(object):
        def __init__(self, name):
            self.name = name

        def write(self, data):
            return len(data)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    return null_file_handle(tile._file_or_url)


def identity_writer(tile, fh):
    assert tile._source_fh_contextmanager is not None
    with tile._source_fh_contextmanager as sfh:
        fh.write(sfh.read())
    return tile.tile_format

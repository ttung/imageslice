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
        checksum_command.add_argument("in_url", help="URL for the source partition file")
        checksum_command.add_argument("out_path", help="Path to write partition file with checksums")
        checksum_command.add_argument("--pretty", action="store_true", help="Pretty-print the output file")

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
            tile_writer=null_writer)


def fake_file_opener(partition_path, tile, ext):
    class fake_handle(object):
        def __init__(self, name):
            self.name = name

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    return fake_handle(tile._file_or_url)


def null_writer(tile, fh):
    pass

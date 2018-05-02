from __future__ import absolute_import, division, print_function, unicode_literals

import argparse

from ._base import CliCommand


def main():
    parser = argparse.ArgumentParser()

    subparser_root = parser.add_subparsers(dest="slicedimage_command_class")

    for cls in CliCommand.__subclasses__():
        subparser = cls.register_parser(subparser_root)
        subparser.set_defaults(slicedimage_command_class=(cls, subparser))

    args, argv = parser.parse_known_args()

    if args.slicedimage_command_class is None:
        parser.print_help()
        parser.exit(status=2)

    cls, subparser = args.slicedimage_command_class

    if len(argv) != 0:
        subparser.print_help()
        parser.exit(status=2)

    cls.run_command(args)

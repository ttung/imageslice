from __future__ import absolute_import, division, print_function, unicode_literals


class CliCommand(object):
    @classmethod
    def register_parser(cls, subparser_root):
        """
        Registers the command's parser arguments.

        :return: the subparser
        """
        raise NotImplementedError()

    @classmethod
    def run_command(cls, args):
        raise NotImplementedError()

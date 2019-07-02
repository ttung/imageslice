import os
import sys


def fspath(pathlib_path):
    if sys.version_info >= (3, 6):
        return os.fspath(pathlib_path)
    else:
        return str(pathlib_path)

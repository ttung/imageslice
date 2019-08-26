import os
import tempfile
import unittest
import uuid
from pathlib import Path

from slicedimage._compat import fspath
from slicedimage.backends import DiskBackend
from slicedimage.url.resolve import resolve_path_or_url, resolve_url


class TestResolvePathOrUrl(unittest.TestCase):
    def test_valid_local_path(self):
        with tempfile.NamedTemporaryFile() as tfn:
            abspath = os.path.realpath(tfn.name)
            _, name, baseurl = resolve_path_or_url(abspath)
            self.assertEqual(name, os.path.basename(abspath))
            self.assertEqual("file://{}".format(os.path.dirname(abspath)), baseurl)

            cwd = os.getcwd()
            try:
                os.chdir(os.path.dirname(abspath))
                _, name, baseurl = resolve_path_or_url(os.path.basename(abspath))
                self.assertEqual(name, os.path.basename(abspath))
                self.assertEqual("file://{}".format(os.path.dirname(abspath)), baseurl)
            finally:
                os.chdir(cwd)

    def test_local_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="c d") as td:
            with tempfile.NamedTemporaryFile(dir=td, prefix="a b") as tfn:
                abspath = Path(tfn.name).resolve()
                backend, name, baseurl = resolve_path_or_url(fspath(abspath))
                self.assertEqual(name, abspath.name)
                self.assertTrue(isinstance(backend, DiskBackend))
                self.assertEqual(fspath(abspath.parent), backend._basedir)
                self.assertEqual(abspath.parent.as_uri(), baseurl)

                with backend.read_contextmanager(name) as rcm:
                    rcm.read()

                cwd = os.getcwd()
                try:
                    os.chdir(fspath(abspath.parent))
                    backend, name, baseurl = resolve_path_or_url(abspath.name)
                    self.assertEqual(name, abspath.name)
                    self.assertTrue(isinstance(backend, DiskBackend))
                    self.assertEqual(fspath(abspath.parent), backend._basedir)
                    self.assertEqual(abspath.parent.as_uri(), baseurl)

                    with backend.read_contextmanager(name) as rcm:
                        rcm.read()
                finally:
                    os.chdir(cwd)

    def test_invalid_local_path(self):
        with self.assertRaises(ValueError):
            resolve_path_or_url(str(uuid.uuid4()))

    def test_url(self):
        _, name, baseurl = resolve_path_or_url("https://github.com/abc/def")
        self.assertEqual(name, "def")
        self.assertEqual(baseurl, "https://github.com/abc")


class TestResolveUrl(unittest.TestCase):
    def test_fully_qualified_url(self):
        _, name, baseurl = resolve_url("https://github.com/abc/def")
        self.assertEqual(name, "def")
        self.assertEqual(baseurl, "https://github.com/abc")

        # even with a baseurl, this should work.
        _, name, baseurl = resolve_url("https://github.com/abc/def", "https://github.io")
        self.assertEqual(name, "def")
        self.assertEqual(baseurl, "https://github.com/abc")

    def test_relative_url(self):
        _, name, baseurl = resolve_url("def", "https://github.com/abc")
        self.assertEqual(name, "def")
        self.assertEqual(baseurl, "https://github.com/abc")

        # even with a path separator in the relative path, it should work.
        _, name, baseurl = resolve_url("abc/def", "https://github.com/")
        self.assertEqual(name, "def")
        self.assertEqual(baseurl, "https://github.com/abc")


if __name__ == "__main__":
    unittest.main()

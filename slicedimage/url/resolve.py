import os
import urllib.parse

import pathlib

from slicedimage._compat import fspath
from slicedimage.backends import CachingBackend, DiskBackend, HttpBackend, S3Backend, SIZE_LIMIT
from .path import join, split


def infer_backend(baseurl, backend_config=None):
    """
    Guess the backend based on the format of `baseurl`, the consistent part of the URL or file path.
    The backend_config dictionary can contain flexible parameters for the different backends.

    Caching parameter keys include:

     - ["caching"]["directory"]  (default: None which disables caching)
     - ["caching"]["debug"]      (default: False)
     - ["caching"]["size_limit"] (default: SIZE_LIMIT)

    """
    if backend_config is None:
        backend_config = {}

    parsed = urllib.parse.urlparse(baseurl)

    if parsed.scheme == "file":
        posix_path = pathlib.PurePosixPath(parsed.path)
        local_path = pathlib.Path(*posix_path.parts)
        return DiskBackend(fspath(local_path))

    if parsed.scheme in ("http", "https"):
        backend = HttpBackend(baseurl)
    elif parsed.scheme == "s3":
        s3_config = backend_config.get("s3", {})
        backend = S3Backend(baseurl, s3_config)
    else:
        raise ValueError(
            "Unable to infer backend for url {}, please verify that baseurl points to a valid "
            "directory or web address".format(baseurl))

    # these backends might use a cache.
    cache_config = backend_config.get("caching", {})

    cache_dir = cache_config.get("directory", None)
    if cache_dir is not None:
        cache_dir = os.path.expanduser(cache_dir)
        size_limit = cache_config.get("size_limit", SIZE_LIMIT)
        if size_limit > 0:
            debug = cache_config.get("debug", False)
            if debug:
                print("> caching {} to {} (size_limit: {})".format(
                    baseurl, cache_dir, size_limit))
            backend = CachingBackend(cache_dir, backend, size_limit)

    return backend


def resolve_path_or_url(path_or_url, backend_config=None):
    """
    Given either a path (absolute or relative), or a URL, attempt to resolve it.  Returns a tuple
    consisting of: a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and
    the baseurl of the object.
    """
    try:
        return resolve_url(path_or_url, backend_config=None)
    except ValueError:
        if os.path.isfile(path_or_url):
            # convert this to a posix path
            native_path = pathlib.Path(path_or_url)
            return resolve_url(
                native_path.name,
                baseurl=native_path.parent.absolute().as_uri(),
                backend_config=backend_config
            )
        raise


def _resolve_absolute_url(absolute_url, backend_config):
    """
    Given a string that is an absolute URL, return a tuple consisting of: a
    :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of
    the object.
    """
    splitted = split(absolute_url)
    backend = infer_backend(splitted[0], backend_config)
    return backend, splitted[1], splitted[0]


def resolve_url(name_or_url, baseurl=None, backend_config=None):
    """
    Given a string that can either be a name or a fully qualified url, return a tuple consisting of:
    a :py:class:`slicedimage.backends._base.Backend`, the basename of the object, and the baseurl of
    the object.

    If the string is a name and not a fully qualified url, then baseurl must be set.  If the string
    is a fully qualified url, then baseurl is ignored.
    """
    try:
        # assume it's a fully qualified url.
        return _resolve_absolute_url(name_or_url, backend_config)
    except ValueError:
        if baseurl is None:
            # oh, we have no baseurl.  punt.
            raise
        absolute_url = join(baseurl, name_or_url)
        return _resolve_absolute_url(absolute_url, backend_config)

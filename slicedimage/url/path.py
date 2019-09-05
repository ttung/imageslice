import os
import pathlib
import posixpath
import urllib.parse
from typing import Optional, Tuple


def join(url: str, *segments) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(
        (parsed.scheme,
         parsed.netloc,
         posixpath.join(parsed.path, *segments),
         parsed.params,
         parsed.query,
         parsed.fragment))


def _parse_absolute_url(absolute_url) -> Tuple[str, str]:
    """
    Given a string that is an absolute URL, return a tuple consisting of the basename of the object
    and the baseurl of the object.
    """
    parsed = urllib.parse.urlparse(absolute_url)
    if len(parsed.scheme) == 0:
        raise ValueError("Not an absolute url.")

    return (
        posixpath.basename(urllib.parse.unquote(parsed.path)),
        urllib.parse.urlunparse(
            (parsed.scheme,
             parsed.netloc,
             posixpath.dirname(parsed.path),
             parsed.params,
             parsed.query,
             parsed.fragment),

        ),
    )


def get_absolute_url(name_or_url: str, baseurl: str = Optional[None]) -> Tuple[str, str]:
    """
    Given a string that can either be a name or an absolute url, return a tuple consisting of the
    basename of the url, and the baseurl of the url.

    If the string is a name and not a fully qualified url, then baseurl must be set.  If the string
    is a fully qualified url, then baseurl is ignored.
    """
    try:
        # assume it's a fully qualified url.
        return _parse_absolute_url(name_or_url)
    except ValueError:
        if baseurl is None:
            # oh, we have no baseurl.  punt.
            raise
        absolute_url = join(baseurl, name_or_url)
        return _parse_absolute_url(absolute_url)


def calculate_relative_url(baseurl: str, name_or_url: str) -> str:
    """
    Given a baseurl and a string that can either be a name or a fully qualified URL, attempt to
    calculate a relative URL.  If it's not possible, return an absolute URL.

    Parameters
    ----------
    baseurl : str
        The base url to calculate the relative URL from.
    name_or_url : str
        The relative or absolute URL.

    Returns
    -------
    str :
        url, relative to baseurl, if url is either already a relative URL, or can be calculated
        relative to baseurl.
    """
    name, new_baseurl = get_absolute_url(name_or_url, baseurl)

    # constitute an absolute URL from the resolved URL.
    absolute_url = join(new_baseurl, name)

    baseurl_parsed = urllib.parse.urlparse(baseurl)
    absolute_url_parsed = urllib.parse.urlparse(absolute_url)

    if baseurl_parsed.scheme != absolute_url_parsed.scheme:
        return absolute_url

    baseurl_path = pathlib.PurePosixPath(baseurl_parsed.path)
    absolute_url_path = pathlib.PurePosixPath(absolute_url_parsed.path)

    try:
        relative_path = absolute_url_path.relative_to(baseurl_path.parent)
    except ValueError:
        # can't make it relative, so return the absolute path.
        return absolute_url

    result = str(relative_path)
    if absolute_url_parsed.params:
        result = result + ";" + absolute_url_parsed.params
    if absolute_url_parsed.query:
        result = result + "?" + absolute_url_parsed.query
    if absolute_url_parsed.fragment:
        result = result + "#" + absolute_url_parsed.fragment

    return result


def get_path_from_parsed_file_url(parsed_file_url: urllib.parse.ParseResult) -> pathlib.Path:
    """If parsed_file_url is the result of parsing a URL using urllib.parse.unparse, and the URL is
    a "file:" URL, then extract the local filesystem path.  Handles idiosyncrasies such as pathlib
    and Windows paths.
    """
    assert parsed_file_url.scheme == "file"
    if os.name == "nt":
        # pathlib can parse c:/windows/xxx, but not /c:/windows/xxx.  however, url paths always
        # start with a /
        return pathlib.Path(urllib.parse.unquote(parsed_file_url.path[1:]))
    else:
        return pathlib.Path(urllib.parse.unquote(parsed_file_url.path))

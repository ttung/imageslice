import posixpath

from six.moves import urllib


def pathsplit(url):
    parsed = urllib.parse.urlparse(url)
    return (
        urllib.parse.urlunparse(
            (parsed.scheme,
             parsed.netloc,
             posixpath.dirname(parsed.path),
             parsed.params,
             parsed.query,
             parsed.fragment),

        ),
        posixpath.basename(parsed.path),
    )


def pathjoin(url, *segments):
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(
        (parsed.scheme,
         parsed.netloc,
         posixpath.join(parsed.path, *segments),
         parsed.params,
         parsed.query,
         parsed.fragment))

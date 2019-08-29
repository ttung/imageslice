from pathlib import Path
from typing import Optional

from diskcache import Cache

from slicedimage.backends import CachingBackend
from slicedimage.backends._base import Backend


class ContextualCachingBackend:
    """
    Provides a context manager for wrapping a caching backend.  This is required for Windows, where
    the cache must be closed before we clean up a working directory.
    """
    def __init__(self, cachedir: Path, authoritative_backend: Backend):
        self.cachedir = cachedir
        self.authoritative_backend = authoritative_backend

    def __enter__(self):
        return CachingBackend(self.cachedir, self.authoritative_backend)

    def __exit__(self, exc_type, exc_val, exc_tb):
        cache_obj = CachingBackend._CACHE.pop(self.cachedir, None)  # type: Optional[Cache]
        if cache_obj is not None:
            cache_obj.close()

import contextlib
import socket

from tests.utils.contextchild import ContextualChildProcess
from tests.utils.contextualcachingbackend import ContextualCachingBackend


def unused_tcp_port():
    """
    Return an unused TCP port.
    """
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def build_skeleton_manifest():
    """
    Returns a 0.0.0 formatted manifest with no tiles.
    """
    return {
        "version": "0.0.0",
        "dimensions": [
            "x",
            "y",
            "hyb",
            "ch"
        ],
        "shape": {
            "hyb": 1,
            "ch": 1
        },
        "tiles": []
    }

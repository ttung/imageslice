import subprocess


class ContextualChildProcess(object):
    """
    Provides a context manager for wrapping a child process.
    """
    def __init__(self, *args, **kwargs):
        self.proc = subprocess.Popen(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.proc.terminate()
        self.proc.wait()

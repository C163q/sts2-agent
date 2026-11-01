import fcntl
from pathlib import Path


class ControllerLease:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.file = None

    def acquire(self):
        if self.file is not None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / ".mcp-controller.lock").open("a")
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.close()
            raise

    def __enter__(self):
        self.acquire()
        return self

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def __exit__(self, *args):
        self.close()

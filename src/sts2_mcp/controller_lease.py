import errno
import os
from pathlib import Path

if os.name == 'nt':
    import msvcrt

    def lock_controller(file):
        file.seek(0)
        try:
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            if error.errno == errno.EACCES:
                raise BlockingIOError(errno.EAGAIN, 'The MCP controller is already held.') from error
            raise
else:
    import fcntl

    def lock_controller(file):
        fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)


class ControllerLease:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.file = None

    def acquire(self):
        if self.file is not None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / ".mcp-controller.lock").open("a+b")
        try:
            lock_controller(self.file)
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

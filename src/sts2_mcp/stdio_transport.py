"""Cancellable streams for the SDK's stdio framing."""
import os

import anyio


POLL_INTERVAL = 0.025


if os.name == 'nt':
    import time
    import _winapi
    import msvcrt

    def configure(descriptor):
        msvcrt.setmode(descriptor, os.O_BINARY)
        os.set_blocking(descriptor, False)

    def read_chunk(descriptor):
        try:
            return os.read(descriptor, 65536)
        except BlockingIOError:
            time.sleep(POLL_INTERVAL)
            return None

    def write_chunk(descriptor, data):
        # Keep the Win32 error code: the CRT maps a disconnected pipe to EINVAL.
        try:
            written, _ = _winapi.WriteFile(msvcrt.get_osfhandle(descriptor), data[:4096])
        except OSError as error:
            if error.winerror in (_winapi.ERROR_BROKEN_PIPE, _winapi.ERROR_NO_DATA):
                raise BrokenPipeError from error
            raise
        if not written:
            time.sleep(POLL_INTERVAL)
        return written
else:
    import select

    def configure(descriptor):
        pass

    def read_chunk(descriptor):
        if select.select([descriptor], [], [], POLL_INTERVAL)[0]:
            return os.read(descriptor, 65536)
        return None

    def write_chunk(descriptor, data):
        if select.select([], [descriptor], [], POLL_INTERVAL)[1]:
            # A ready POSIX pipe accepts PIPE_BUF bytes without blocking.
            return os.write(descriptor, data[:select.PIPE_BUF])
        return 0


class Stdin:
    def __init__(self, descriptor, cancel_scope):
        configure(descriptor)
        self.descriptor = descriptor
        self.cancel_scope = cancel_scope
        self.buffer = b''
        self.eof = False

    def _readline(self):
        while b'\n' not in self.buffer and not self.eof:
            anyio.from_thread.check_cancelled()
            chunk = read_chunk(self.descriptor)
            if chunk is not None:
                self.buffer += chunk
                self.eof = not chunk
        line, separator, self.buffer = self.buffer.partition(b'\n')
        return (line + separator).decode('utf-8')

    async def __aiter__(self):
        while line := await anyio.to_thread.run_sync(self._readline):
            yield line
        # EOF also stops tool handlers waiting on game responses.
        self.cancel_scope.cancel()


class Stdout:
    def __init__(self, descriptor, cancel_scope):
        configure(descriptor)
        self.descriptor = descriptor
        self.cancel_scope = cancel_scope

    def _write(self, data):
        remaining = memoryview(data)
        while remaining:
            anyio.from_thread.check_cancelled()
            written = write_chunk(self.descriptor, remaining)
            remaining = remaining[written:]

    async def write(self, text):
        try:
            await anyio.to_thread.run_sync(self._write, text.encode('utf-8'))
        except BrokenPipeError:
            self.cancel_scope.cancel()

    async def flush(self):
        # Writes go directly to the descriptor, so no buffered data remains.
        await anyio.lowlevel.checkpoint()

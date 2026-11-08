"""Cancellable POSIX streams for the SDK's stdio framing."""
import os
import select

import anyio


class Stdin:
    def __init__(self, descriptor, cancel_scope):
        self.descriptor = descriptor
        self.cancel_scope = cancel_scope
        self.buffer = b''
        self.eof = False

    def _readline(self):
        while b'\n' not in self.buffer and not self.eof:
            anyio.from_thread.check_cancelled()
            if select.select([self.descriptor], [], [], 0.025)[0]:
                chunk = os.read(self.descriptor, 65536)
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
        self.descriptor = descriptor
        self.cancel_scope = cancel_scope

    def _write(self, data):
        remaining = memoryview(data)
        while remaining:
            anyio.from_thread.check_cancelled()
            if select.select([], [self.descriptor], [], 0.025)[1]:
                # A ready POSIX pipe accepts PIPE_BUF bytes without blocking.
                written = os.write(self.descriptor, remaining[:select.PIPE_BUF])
                remaining = remaining[written:]

    async def write(self, text):
        try:
            await anyio.to_thread.run_sync(self._write, text.encode('utf-8'))
        except BrokenPipeError:
            self.cancel_scope.cancel()

    async def flush(self):
        # Writes go directly to the descriptor, so no buffered data remains.
        await anyio.lowlevel.checkpoint()

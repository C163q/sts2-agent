"""Public tool facade; normalization and session execution have separate owners."""
from sts2_mcp.tool_registry import TOOLS, SPECS
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.game_session import GameSession
from sts2_mcp.output.error_output import invalid_request
from sts2_mcp.screenshot_tool import screenshots_disabled


class GameTools:
    def __init__(self, client, controller=None, screenshot_directory=None):
        self.session = GameSession(client, controller, screenshot_directory)

    @property
    def client(self): return self.session.client
    @property
    def lock(self): return self.session.lock
    @property
    def screenshots(self): return self.session.screenshots
    @property
    def controller(self): return self.session.controller
    @controller.setter
    def controller(self, value): self.session.controller = value
    @property
    def snapshot_id(self): return self.session.permission.token
    @snapshot_id.setter
    def snapshot_id(self, value): self.session.permission.replace(value)

    async def invoke(self, name, arguments=None):
        try:
            request = normalize_request(TOOLS[name], arguments)
            if request.effect == 'file' and self.screenshots is None:
                return screenshots_disabled()
        except ValueError as error:
            return invalid_request(str(error))
        return await self.session.execute(request)


def _handler(spec):
    async def handle(self, arguments=None):
        return await self.invoke(spec.name, arguments)
    handle.__name__ = spec.name
    handle.__doc__ = spec.description
    handle.supports_output_presets = bool(spec.presets)
    return handle


for _spec in SPECS:
    setattr(GameTools, _spec.name, _handler(_spec))

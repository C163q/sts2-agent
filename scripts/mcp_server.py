"""Compatibility command entry point; implementation lives in sts2_mcp."""
from _bootstrap import ROOT
from sts2_mcp.mcp_server import ControllerLease, GameTools, create_server, main, run_stdio, tool_result


if __name__ == "__main__":
    main()

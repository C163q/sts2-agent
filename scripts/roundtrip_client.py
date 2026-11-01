"""Compatibility command entry point; implementation lives in sts2_mcp."""
from _bootstrap import ROOT
from sts2_mcp.roundtrip_client import Client, main, player_result


if __name__ == "__main__":
    main()

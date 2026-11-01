"""Compatibility entry point for the isolated graphical test suite."""
from _bootstrap import ROOT
from tests.game.suite import GameSession, execute_cases, load_cases, main


if __name__ == "__main__":
    main()

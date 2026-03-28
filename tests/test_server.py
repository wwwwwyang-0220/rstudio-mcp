from pathlib import Path
from unittest.mock import patch
import pytest


def test_main_default_config(monkeypatch):
    from rstudio_mcp import server
    monkeypatch.setattr("sys.argv", ["rstudio-mcp"])
    with patch.object(server._mcp, "run"):
        server.main()
    assert server._config.host == "localhost"
    assert server._config.port == 6311
    assert server._config.execution_enabled is False
    assert server._config.allowed_dirs == []


def test_main_custom_host_and_port(monkeypatch):
    from rstudio_mcp import server
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--host", "127.0.0.1", "--port", "9999"])
    with patch.object(server._mcp, "run"):
        server.main()
    assert server._config.host == "127.0.0.1"
    assert server._config.port == 9999


def test_main_execution_flag(monkeypatch):
    from rstudio_mcp import server
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--enable-execution"])
    with patch.object(server._mcp, "run"):
        server.main()
    assert server._config.execution_enabled is True


def test_main_allow_dir_adds_to_allowed_dirs(monkeypatch, tmp_path):
    from rstudio_mcp import server
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--allow-dir", str(tmp_path)])
    with patch.object(server._mcp, "run"):
        server.main()
    assert tmp_path in server._config.allowed_dirs


def test_main_multiple_allow_dirs(monkeypatch, tmp_path):
    from rstudio_mcp import server
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    monkeypatch.setattr(
        "sys.argv",
        ["rstudio-mcp", "--allow-dir", str(dir_a), "--allow-dir", str(dir_b)],
    )
    with patch.object(server._mcp, "run"):
        server.main()
    assert dir_a in server._config.allowed_dirs
    assert dir_b in server._config.allowed_dirs

from pathlib import Path
from unittest.mock import patch
import pytest


def test_main_default_config(monkeypatch):
    from rstudio_mcp import server
    monkeypatch.setattr("sys.argv", ["rstudio-mcp"])
    with patch.object(server._mcp, "run"):
        server.main()
    assert server._config.host == "127.0.0.1"
    assert server._config.port == 6312
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


def test_install_auto_start_creates_bootstrap_and_rprofile(monkeypatch, tmp_path, capsys):
    from rstudio_mcp import server

    monkeypatch.setattr(server.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--install-auto-start"])

    server.main()

    bootstrap = tmp_path / ".rstudio-mcp" / "bootstrap.R"
    rprofile = tmp_path / ".Rprofile"
    assert bootstrap.exists()
    assert "httpuv::startServer" in bootstrap.read_text(encoding="utf-8")
    assert rprofile.exists()
    assert server._RPROFILE_SNIPPET in rprofile.read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert "Installed auto-start" in out


def test_install_auto_start_is_idempotent(monkeypatch, tmp_path):
    from rstudio_mcp import server

    monkeypatch.setattr(server.Path, "home", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--install-auto-start"])

    server.main()
    server.main()

    rprofile = (tmp_path / ".Rprofile").read_text(encoding="utf-8")
    assert rprofile.count(server._RPROFILE_SNIPPET) == 1


def test_uninstall_auto_start_removes_snippet_but_keeps_bootstrap(monkeypatch, tmp_path, capsys):
    from rstudio_mcp import server

    monkeypatch.setattr(server.Path, "home", lambda: tmp_path)
    (tmp_path / ".rstudio-mcp").mkdir()
    bootstrap = tmp_path / ".rstudio-mcp" / "bootstrap.R"
    bootstrap.write_text("bootstrap", encoding="utf-8")
    (tmp_path / ".Rprofile").write_text(
        "options(stringsAsFactors = FALSE)\n"
        f"{server._RPROFILE_SNIPPET}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["rstudio-mcp", "--uninstall-auto-start"])

    server.main()

    assert bootstrap.exists()
    rprofile = (tmp_path / ".Rprofile").read_text(encoding="utf-8")
    assert server._RPROFILE_SNIPPET not in rprofile
    assert "options(stringsAsFactors = FALSE)" in rprofile
    out = capsys.readouterr().out
    assert "Removed auto-start" in out

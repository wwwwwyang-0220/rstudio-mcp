from pathlib import Path
import pytest
from rstudio_mcp.config import ServerConfig


def test_default_config():
    cfg = ServerConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 6312
    assert cfg.allowed_dirs == []
    assert cfg.execution_enabled is False


def test_is_path_allowed_inside_authorized_dir(tmp_path):
    cfg = ServerConfig(allowed_dirs=[tmp_path])
    assert cfg.is_path_allowed(tmp_path / "analysis.R") is True


def test_is_path_allowed_outside_authorized_dir(tmp_path):
    authorized = tmp_path / "scripts"
    authorized.mkdir()
    cfg = ServerConfig(allowed_dirs=[authorized])
    other = tmp_path / "other.R"
    other.write_text("")
    assert cfg.is_path_allowed(other) is False


def test_is_path_allowed_path_traversal_blocked(tmp_path):
    authorized = tmp_path / "scripts"
    authorized.mkdir()
    cfg = ServerConfig(allowed_dirs=[authorized])
    traversal = authorized / ".." / ".." / "etc" / "passwd"
    assert cfg.is_path_allowed(traversal) is False


def test_is_path_allowed_no_dirs_always_false(tmp_path):
    cfg = ServerConfig(allowed_dirs=[])
    assert cfg.is_path_allowed(tmp_path / "anything.R") is False


def test_multiple_allowed_dirs(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    cfg = ServerConfig(allowed_dirs=[dir_a, dir_b])
    assert cfg.is_path_allowed(dir_a / "script.R") is True
    assert cfg.is_path_allowed(dir_b / "script.R") is True
    assert cfg.is_path_allowed(tmp_path / "outside.R") is False

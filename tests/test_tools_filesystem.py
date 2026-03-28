import pytest
from pathlib import Path
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.tools.filesystem import r_list_scripts, r_read_script


# ── fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def r_dir(tmp_path):
    (tmp_path / "analysis.R").write_text("x <- 1\nprint(x)\n", encoding="utf-8")
    (tmp_path / "model.R").write_text("lm(y ~ x, data = df)\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not an R file\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def config(r_dir):
    return ServerConfig(allowed_dirs=[r_dir])


# ── r_list_scripts ─────────────────────────────────────────────────────────────

def test_r_list_scripts_returns_r_files_only(config, r_dir):
    result = r_list_scripts(config, str(r_dir))
    assert "analysis.R" in result
    assert "model.R" in result
    assert "notes.txt" not in result


def test_r_list_scripts_unauthorized_dir_returns_error(tmp_path):
    cfg = ServerConfig(allowed_dirs=[tmp_path / "authorized"])
    other = tmp_path / "other"
    other.mkdir()
    result = r_list_scripts(cfg, str(other))
    assert "Error" in result
    assert "authorized" in result.lower()


def test_r_list_scripts_nonexistent_dir_returns_error(tmp_path):
    cfg = ServerConfig(allowed_dirs=[tmp_path / "authorized"])
    result = r_list_scripts(cfg, str(tmp_path / "nonexistent"))
    assert "Error" in result


def test_r_list_scripts_empty_dir(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    cfg = ServerConfig(allowed_dirs=[empty])
    result = r_list_scripts(cfg, str(empty))
    assert "no .R files" in result


def test_r_list_scripts_not_a_directory(config, r_dir):
    result = r_list_scripts(config, str(r_dir / "analysis.R"))
    assert "Error" in result
    assert "not a directory" in result.lower()


# ── r_read_script ──────────────────────────────────────────────────────────────

def test_r_read_script_returns_file_content(config, r_dir):
    result = r_read_script(config, str(r_dir / "analysis.R"))
    assert result == "x <- 1\nprint(x)\n"


def test_r_read_script_unauthorized_path_returns_error(tmp_path):
    cfg = ServerConfig(allowed_dirs=[tmp_path / "allowed"])
    secret = tmp_path / "secret.R"
    secret.write_text("secret code\n")
    result = r_read_script(cfg, str(secret))
    assert "Error" in result
    assert "authorized" in result.lower()


def test_r_read_script_nonexistent_file_returns_error(config, r_dir):
    result = r_read_script(config, str(r_dir / "missing.R"))
    assert "Error" in result
    assert "does not exist" in result.lower()


def test_r_read_script_non_r_extension_returns_error(config, r_dir):
    result = r_read_script(config, str(r_dir / "notes.txt"))
    assert "Error" in result
    assert ".R" in result or "not an .R" in result.lower()


def test_r_read_script_path_traversal_blocked(config, r_dir):
    traversal = str(r_dir / ".." / ".." / "etc" / "passwd")
    result = r_read_script(config, traversal)
    assert "Error" in result


def test_r_read_script_case_insensitive_extension(config, r_dir):
    """Both .R and .r extensions are valid."""
    lower_r = r_dir / "script.r"
    lower_r.write_text("y <- 2\n", encoding="utf-8")
    result = r_read_script(config, str(lower_r))
    assert result == "y <- 2\n"

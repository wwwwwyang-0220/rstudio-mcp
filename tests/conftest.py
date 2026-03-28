import pytest
from pathlib import Path
from rstudio_mcp.config import ServerConfig


@pytest.fixture
def tmp_r_dir(tmp_path):
    """Temp directory with two .R files for filesystem tests."""
    (tmp_path / "script_a.R").write_text("x <- 1\nprint(x)\n", encoding="utf-8")
    (tmp_path / "script_b.R").write_text("y <- 2\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def authorized_config(tmp_r_dir):
    return ServerConfig(allowed_dirs=[tmp_r_dir])

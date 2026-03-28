from __future__ import annotations
from pathlib import Path
from rstudio_mcp.config import ServerConfig


def r_list_scripts(config: ServerConfig, directory: str) -> str:
    """Lists .R files in an authorized directory."""
    target = Path(directory)
    if not config.is_path_allowed(target):
        return f"Error: Directory '{directory}' is not within an authorized path."
    if not target.exists() or not target.is_dir():
        return f"Error: '{directory}' is not a directory."
    scripts = sorted(target.glob("*.[Rr]"))
    if not scripts:
        return "(no .R files found)"
    return "\n".join(str(p) for p in scripts)


def r_read_script(config: ServerConfig, path: str) -> str:
    """Returns full text content of an authorized .R file."""
    target = Path(path)
    if not config.is_path_allowed(target):
        return f"Error: Path '{path}' is not within an authorized directory."
    if not target.exists():
        return f"Error: File '{path}' does not exist."
    if target.suffix.lower() != ".r":
        return f"Error: File '{path}' is not an .R file (suffix must be .R or .r)."
    return target.read_text(encoding="utf-8")

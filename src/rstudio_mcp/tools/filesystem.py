from __future__ import annotations
from pathlib import Path
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.rserve_client import RserveClient


def _resolve_allowed_dirs(config: ServerConfig, client: RserveClient) -> list[Path]:
    """Return configured dirs, or auto-detect from R's getwd() if none configured.

    Falls back to the process CWD if Rserve is unreachable.
    """
    if config.allowed_dirs:
        return list(config.allowed_dirs)
    try:
        r_wd = client.eval_r("getwd()")
        return [Path(str(r_wd))]
    except Exception:
        return [Path.cwd()]


def _is_path_allowed(path: Path, allowed_dirs: list[Path]) -> bool:
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(d).resolve()) for d in allowed_dirs)


def r_list_scripts(config: ServerConfig, client: RserveClient, directory: str) -> str:
    """Lists .R files in an authorized directory."""
    allowed = _resolve_allowed_dirs(config, client)
    target = Path(directory)
    if not _is_path_allowed(target, allowed):
        return f"Error: Directory '{directory}' is not within an authorized path."
    if not target.exists() or not target.is_dir():
        return f"Error: '{directory}' is not a directory."
    scripts = sorted(target.glob("*.[Rr]"))
    if not scripts:
        return "(no .R files found)"
    return "\n".join(str(p) for p in scripts)


def r_read_script(config: ServerConfig, client: RserveClient, path: str) -> str:
    """Returns full text content of an authorized .R file."""
    allowed = _resolve_allowed_dirs(config, client)
    target = Path(path)
    if not _is_path_allowed(target, allowed):
        return f"Error: Path '{path}' is not within an authorized directory."
    if not target.exists():
        return f"Error: File '{path}' does not exist."
    if target.suffix.lower() != ".r":
        return f"Error: File '{path}' is not an .R file (suffix must be .R or .r)."
    return target.read_text(encoding="utf-8")

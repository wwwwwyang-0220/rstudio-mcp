from __future__ import annotations
import json
from rstudio_mcp.rserve_client import RserveClient, RserveConnectionError, RserveEvalError

# R expression: read last N lines from .Rhistory in working directory.
# savehistory() is unavailable in non-interactive Rserve context.
_HISTORY_EXPR = """\
local({{
  hist_file <- file.path(getwd(), ".Rhistory")
  if (file.exists(hist_file)) {{
    lines <- readLines(hist_file, warn = FALSE)
    tail(lines, {n})
  }} else {{
    character(0)
  }}
}})"""


def _session_recovery_step(client: RserveClient) -> dict[str, str]:
    return {
        "command": "rstudio-mcp --print-r-server",
        "instructions": (
            "Run the command in a terminal, paste the printed R code into the "
            "RStudio Console, execute it, and retry after RStudio reports that "
            "the MCP httpuv server has started."
        ),
    }


def r_list_objects(client: RserveClient) -> str:
    """Returns JSON array of all object names in .GlobalEnv."""
    try:
        raw = client.eval_r("ls()")
        if raw is None:
            names: list[str] = []
        elif isinstance(raw, str):
            names = [raw]
        else:
            names = list(raw)
        return json.dumps(names)
    except (RserveConnectionError, RserveEvalError) as exc:
        return json.dumps({"error": str(exc)})


def r_describe_object(client: RserveClient, name: str) -> str:
    """Returns structural description of named object via str()."""
    try:
        lines = client.eval_capture(f"str({name})")
        return "\n".join(lines)
    except RserveEvalError as exc:
        return f"Error: {exc}"
    except RserveConnectionError as exc:
        return f"Connection error: {exc}"


def r_preview_object(client: RserveClient, name: str, n: int = 10) -> str:
    """Returns first n rows of tabular object via head()."""
    try:
        lines = client.eval_capture(f"head({name}, {n})")
        return "\n".join(lines)
    except RserveEvalError as exc:
        return f"Error: {exc}"
    except RserveConnectionError as exc:
        return f"Connection error: {exc}"


def r_summarize_object(client: RserveClient, name: str) -> str:
    """Returns descriptive statistics via summary()."""
    try:
        lines = client.eval_capture(f"summary({name})")
        return "\n".join(lines)
    except RserveEvalError as exc:
        return f"Error: {exc}"
    except RserveConnectionError as exc:
        return f"Connection error: {exc}"


def r_check_session(client: RserveClient) -> str:
    """Checks connected R session health.

    Returns JSON with connected status, pid, R version, and working directory.
    """
    _CHECK_EXPR = """\
local({
  list(
    pid     = Sys.getpid(),
    version = R.version$version.string,
    wd      = getwd()
  )
})"""
    try:
        result = client.eval_r(_CHECK_EXPR)
        return json.dumps({
            "connected": True,
            "pid": int(result["pid"]),
            "r_version": str(result["version"]),
            "working_directory": str(result["wd"]),
        })
    except (RserveConnectionError, RserveEvalError) as exc:
        return json.dumps({
            "connected": False,
            "error": str(exc),
            "next_step": _session_recovery_step(client),
        })


def r_get_history(client: RserveClient, n: int = 20) -> str:
    """Returns last n commands as JSON array, read from .Rhistory in R working dir."""
    expr = _HISTORY_EXPR.format(n=n)
    try:
        raw = client.eval_r(expr)
        if raw is None:
            lines: list[str] = []
        elif isinstance(raw, str):
            lines = [raw]
        else:
            lines = list(raw)
        return json.dumps(lines)
    except (RserveConnectionError, RserveEvalError) as exc:
        return json.dumps({"error": str(exc)})

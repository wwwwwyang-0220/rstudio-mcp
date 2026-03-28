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

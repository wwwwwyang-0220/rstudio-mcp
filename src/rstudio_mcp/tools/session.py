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


def r_check_session(client: RserveClient) -> str:
    """Checks connected R session health and warns if multiple Rserve processes are detected.

    Returns JSON with pid, R version, working directory, rserve_process_count,
    and an actionable warning message when count > 1.
    """
    # Count Rserve processes via shell from within R.
    # pgrep is available on macOS and Linux; falls back to 1 on error.
    _CHECK_EXPR = """\
local({
  pid     <- Sys.getpid()
  version <- R.version$version.string
  wd      <- getwd()
  count   <- tryCatch(
    as.integer(system("pgrep -c Rserve 2>/dev/null", intern = TRUE)),
    warning = function(w) 1L,
    error   = function(e) 1L
  )
  if (length(count) == 0 || is.na(count)) count <- 1L
  list(pid = pid, version = version, wd = wd, count = count)
})"""
    try:
        result = client.eval_r(_CHECK_EXPR)
        pid     = int(result["pid"])
        version = str(result["version"])
        wd      = str(result["wd"])
        count   = int(result["count"])

        info: dict = {
            "connected": True,
            "pid": pid,
            "r_version": version,
            "working_directory": wd,
            "rserve_process_count": count,
        }

        if count > 1:
            info["warning"] = (
                f"检测到 {count} 个 Rserve 进程正在运行。"
                "MCP 很可能连接到了一个旧的后台 R 进程，而不是你当前的交互式 RStudio 会话，"
                "这会导致你在 RStudio 里看不到 MCP 创建的变量。"
                "修复方法：\n"
                "  1. 在终端运行：pkill -f Rserve\n"
                "  2. 在你当前的 RStudio 控制台重新运行：\n"
                "       library(Rserve)\n"
                "       Rserve(args='--no-save')"
            )

        return json.dumps(info, ensure_ascii=False)
    except (RserveConnectionError, RserveEvalError) as exc:
        return json.dumps({"connected": False, "error": str(exc)})


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

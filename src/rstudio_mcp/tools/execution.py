from __future__ import annotations
import json
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.rserve_client import RserveClient, RserveConnectionError, RserveEvalError

_EVAL_EXPR = "capture.output(eval(parse(text=.__mcp_expr__), envir=.GlobalEnv))"


def r_execute_code(
    config: ServerConfig, client: RserveClient, expression: str
) -> str:
    """Execute R expression in .GlobalEnv and return stdout + stderr as JSON.

    Disabled by default; requires config.execution_enabled = True.
    Expression is passed via pyRserve variable assignment to avoid all
    string-escaping issues (quotes, backslashes, newlines all safe).
    """
    if not config.execution_enabled:
        return json.dumps({
            "error": (
                "Execution mode is disabled. "
                "Start the server with --enable-execution to allow code execution."
            )
        })

    try:
        # Assign expression string to R variable (pyRserve handles serialization)
        client.assign_r(".__mcp_expr__", expression)

        # Evaluate and capture printed output
        raw = client.eval_r(_EVAL_EXPR)

        # Clean up temp variable from .GlobalEnv
        client.eval_r("rm(.__mcp_expr__)")

        if raw is None:
            stdout: list[str] = []
        elif isinstance(raw, str):
            stdout = [raw]
        else:
            stdout = list(raw)

        return json.dumps({"stdout": stdout, "stderr": []})

    except RserveEvalError as exc:
        return json.dumps({"stdout": [], "stderr": [str(exc)]})
    except RserveConnectionError as exc:
        return json.dumps({"error": str(exc)})

from __future__ import annotations
import json
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.rserve_client import RserveClient, RserveConnectionError, RserveEvalError

def r_execute_code(
    config: ServerConfig, client: RserveClient, expression: str
) -> str:
    """Execute R expression in .GlobalEnv and return stdout + stderr as JSON.

    Disabled by default; requires config.execution_enabled = True.
    json.dumps() produces a valid R string literal (double-quoted, special chars
    escaped), so the expression is embedded directly — no temp variable needed.
    """
    if not config.execution_enabled:
        return json.dumps({
            "error": (
                "Execution mode is disabled. "
                "Start the server with --enable-execution to allow code execution."
            )
        })

    try:
        # Embed expression as a JSON string literal (valid R string syntax)
        r_code = f"capture.output(eval(parse(text={json.dumps(expression)}), envir=.GlobalEnv))"
        raw = client.eval_r(r_code)

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

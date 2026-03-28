from __future__ import annotations
import json
import urllib.request
import urllib.error


class RserveConnectionError(Exception):
    """Raised when the httpuv R server cannot be reached."""


class RserveEvalError(Exception):
    """Raised when R returns an error from evaluating an expression."""


class RHttpClient:
    """HTTP client for the in-process httpuv R server.

    Provides the same interface as the old RserveClient so all tools work
    unchanged.  connect() and close() are no-ops (httpuv lives in-process).
    assign_r() is a no-op because eval_r() / r_execute_code() operate directly
    in .GlobalEnv via httpuv — no variable bridging needed.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6312) -> None:
        self._host = host
        self._port = port
        self._url = f"http://{host}:{port}/mcp"

    # ── public interface (mirrors RserveClient) ────────────────────────────

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def assign_r(self, name: str, value: object) -> None:
        """No-op: httpuv evaluates directly in .GlobalEnv; no bridging needed."""

    def eval_r(self, expression: str) -> object:
        """Evaluate R expression and return the Python-decoded result value.

        The R server serialises the result with jsonlite::toJSON and returns it
        as a JSON string inside {"value": "...", "error": null}.
        Returns None when the expression produces no printable value.
        """
        resp = self._post(expression, mode="value")
        raw = resp.get("value")
        if raw is None:
            return None
        return json.loads(raw)

    def eval_capture(self, expression: str) -> list[str]:
        """Evaluate R expression and return captured stdout lines."""
        resp = self._post(expression, mode="capture")
        raw = resp.get("stdout") or []
        # Flatten: guard against jsonlite returning [["line"]] instead of ["line"]
        result = []
        for item in raw:
            if isinstance(item, list):
                result.extend(str(x) for x in item)
            else:
                result.append(str(item))
        return result

    # ── internal ───────────────────────────────────────────────────────────

    def _post(self, expression: str, *, mode: str) -> dict:
        body = json.dumps({"expression": expression, "mode": mode}).encode()
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RserveConnectionError(self.connection_help(str(exc))) from exc

        if payload.get("error"):
            raise RserveEvalError(payload["error"])
        return payload

    def connection_help(self, detail: str | None = None) -> str:
        location = f"http://{self._host}:{self._port}/mcp"
        message = (
            "RStudio session bridge is not running or not reachable at "
            f"{location}. "
            "In a terminal, run `rstudio-mcp --print-r-server`, then paste the "
            "printed R code into the RStudio Console and execute it. "
            f"When RStudio shows `MCP httpuv server started on {self._host}:{self._port}`, "
            "retry the MCP command."
        )
        if detail:
            return f"{message} Underlying error: {detail}"
        return message

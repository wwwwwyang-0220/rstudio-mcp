from __future__ import annotations
import pyRserve
import pyRserve.rexceptions as _rexc

# Actual pyRserve exception for R-level eval failures
_R_EVAL_EXC = _rexc.REvalError


class RserveConnectionError(Exception):
    pass


class RserveEvalError(Exception):
    pass


class RserveClient:
    def __init__(self, host: str = "localhost", port: int = 6311) -> None:
        self._host = host
        self._port = port
        self._conn: pyRserve.rserve.RserveConnection | None = None

    def connect(self) -> None:
        """Open TCP connection to Rserve. Raises RserveConnectionError on failure."""
        try:
            self._conn = pyRserve.connect(host=self._host, port=self._port)
        except Exception as exc:
            raise RserveConnectionError(
                f"Failed to connect to Rserve at {self._host}:{self._port}: {exc}"
            ) from exc

    def close(self) -> None:
        """Close the connection if open."""
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def eval_r(self, expression: str) -> object:
        """Evaluate R expression; connect lazily. Raises RserveEvalError or RserveConnectionError."""
        if self._conn is None:
            self.connect()
        try:
            return self._conn.eval(expression)
        except _R_EVAL_EXC as exc:
            raise RserveEvalError(f"R evaluation error: {exc}") from exc
        except Exception as exc:
            self._conn = None
            raise RserveConnectionError(f"Connection lost: {exc}") from exc

    def eval_capture(self, expression: str) -> list[str]:
        """Evaluate R expression wrapped in capture.output(); returns list of strings.

        Normalizes pyRserve's varied return types:
          - list[str]  → returned as-is
          - str        → wrapped in list (single-element R vector)
          - None       → empty list (R NULL)
        """
        result = self.eval_r(f"capture.output({expression})")
        if result is None:
            return []
        if isinstance(result, str):
            return [result]
        return list(result)

    def assign_r(self, name: str, value: object) -> None:
        """Assign a Python value to an R variable using pyRserve serialization.

        Use this instead of string interpolation to avoid escaping issues.
        The pyRserve layer handles Python str -> R character conversion safely.
        """
        if self._conn is None:
            self.connect()
        try:
            self._conn.r[name] = value
        except Exception as exc:
            raise RserveEvalError(f"Failed to assign R variable '{name}': {exc}") from exc

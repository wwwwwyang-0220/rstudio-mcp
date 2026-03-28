import json
from unittest.mock import MagicMock
import pytest
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.tools.execution import r_execute_code
from rstudio_mcp.rserve_client import RserveEvalError, RserveConnectionError


# ── helpers ───────────────────────────────────────────────────────────────────

def make_client(eval_r_return=None):
    client = MagicMock()
    client.eval_r.return_value = eval_r_return
    return client


def enabled_config():
    return ServerConfig(execution_enabled=True)


def disabled_config():
    return ServerConfig(execution_enabled=False)


# ── disabled by default ───────────────────────────────────────────────────────

def test_execute_disabled_returns_error_json():
    result = json.loads(r_execute_code(disabled_config(), make_client(), "1 + 1"))
    assert "error" in result
    assert "disabled" in result["error"].lower()


def test_execute_disabled_never_calls_rserve():
    client = make_client()
    r_execute_code(disabled_config(), client, "1 + 1")
    client.eval_r.assert_not_called()


# ── enabled execution ─────────────────────────────────────────────────────────

def test_execute_enabled_returns_stdout():
    client = make_client(eval_r_return=["[1] 2"])
    result = json.loads(r_execute_code(enabled_config(), client, "1 + 1"))
    assert result["stdout"] == ["[1] 2"]
    assert result["stderr"] == []


def test_execute_embeds_expression_via_json_dumps():
    """Expression must be embedded as json.dumps() string literal, not via temp variable."""
    client = make_client(eval_r_return=[])
    expression = 'x <- "hello world"\nprint(x)'
    r_execute_code(enabled_config(), client, expression)
    call_expr = client.eval_r.call_args[0][0]
    # json.dumps produces the expression as a valid JSON/R string inside the R call
    assert json.dumps(expression) in call_expr
    assert "parse(text=" in call_expr
    assert ".__mcp_expr__" not in call_expr  # old temp-variable approach must NOT be used


def test_execute_special_chars_in_expression():
    """Expressions with quotes, backslashes, newlines must work via json.dumps embedding."""
    client = make_client(eval_r_return=["[1] \"hello\""])
    expression = 'cat("hello\\nworld")'
    r_execute_code(enabled_config(), client, expression)
    call_expr = client.eval_r.call_args[0][0]
    assert json.dumps(expression) in call_expr


def test_execute_empty_output_returns_empty_stdout():
    client = make_client(eval_r_return=None)
    result = json.loads(r_execute_code(enabled_config(), client, "invisible(NULL)"))
    assert result["stdout"] == []
    assert result["stderr"] == []


def test_execute_single_line_output_normalized():
    """pyRserve may return str for single-line output."""
    client = make_client(eval_r_return="[1] TRUE")
    result = json.loads(r_execute_code(enabled_config(), client, "TRUE"))
    assert result["stdout"] == ["[1] TRUE"]


# ── error handling ────────────────────────────────────────────────────────────

def test_execute_r_eval_error_returns_stderr():
    client = MagicMock()
    client.eval_r.side_effect = RserveEvalError("object 'x' not found")
    result = json.loads(r_execute_code(enabled_config(), client, "x"))
    assert result["stdout"] == []
    assert "not found" in result["stderr"][0]


def test_execute_connection_error_returns_error_json():
    client = MagicMock()
    client.eval_r.side_effect = RserveConnectionError("refused")
    result = json.loads(r_execute_code(enabled_config(), client, "1 + 1"))
    assert "error" in result

from unittest.mock import MagicMock
import json
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
    client = make_client()
    result = json.loads(r_execute_code(disabled_config(), client, "1 + 1"))
    assert "error" in result
    assert "disabled" in result["error"].lower()


def test_execute_disabled_never_calls_rserve():
    client = make_client()
    r_execute_code(disabled_config(), client, "1 + 1")
    client.assign_r.assert_not_called()
    client.eval_r.assert_not_called()


# ── enabled execution ─────────────────────────────────────────────────────────

def test_execute_enabled_returns_stdout():
    client = make_client(eval_r_return=["[1] 2"])
    result = json.loads(r_execute_code(enabled_config(), client, "1 + 1"))
    assert result["stdout"] == ["[1] 2"]
    assert result["stderr"] == []


def test_execute_assigns_expression_to_temp_var():
    """Expression must be assigned via assign_r to avoid escaping issues."""
    client = make_client(eval_r_return=[])
    r_execute_code(enabled_config(), client, 'x <- "hello world"')
    client.assign_r.assert_any_call(".__mcp_expr__", 'x <- "hello world"')


def test_execute_evals_via_parse_text_temp_var():
    """R eval must reference the temp variable, not an inline string."""
    client = make_client(eval_r_return=[])
    r_execute_code(enabled_config(), client, "1 + 1")
    eval_calls = [str(c) for c in client.eval_r.call_args_list]
    assert any(".__mcp_expr__" in c for c in eval_calls)


def test_execute_cleans_up_temp_var():
    """.__mcp_expr__ must be removed from .GlobalEnv after execution."""
    client = make_client(eval_r_return=[])
    r_execute_code(enabled_config(), client, "1 + 1")
    eval_calls = [str(c) for c in client.eval_r.call_args_list]
    assert any("rm(.__mcp_expr__)" in c for c in eval_calls)


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
    assert len(result["stderr"]) > 0
    assert "not found" in result["stderr"][0]


def test_execute_connection_error_returns_error_json():
    client = MagicMock()
    client.eval_r.side_effect = RserveConnectionError("refused")
    result = json.loads(r_execute_code(enabled_config(), client, "1 + 1"))
    assert "error" in result

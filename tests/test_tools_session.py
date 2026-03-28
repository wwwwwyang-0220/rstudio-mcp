from unittest.mock import MagicMock
import json
import pytest
from rstudio_mcp.tools.session import (
    r_check_session,
    r_list_objects,
    r_describe_object,
    r_preview_object,
    r_summarize_object,
    r_get_history,
)
from rstudio_mcp.rserve_client import RserveEvalError, RserveConnectionError


# ── helpers ───────────────────────────────────────────────────────────────────

def make_client(*, eval_r=None, eval_capture=None):
    client = MagicMock()
    client.eval_r.return_value = eval_r
    client.eval_capture.return_value = eval_capture or []
    return client


# ── r_check_session ───────────────────────────────────────────────────────────

def _mock_session_result(count=1):
    """Build the dict that pyRserve would return from the r_check_session R expression."""
    return {"pid": 12345, "version": "R version 4.5.1", "wd": "/Users/test", "count": count}


def test_r_check_session_healthy_returns_json():
    client = make_client(eval_r=_mock_session_result(count=1))
    result = json.loads(r_check_session(client))
    assert result["connected"] is True
    assert result["pid"] == 12345
    assert result["rserve_process_count"] == 1
    assert "warning" not in result


def test_r_check_session_multiple_rserve_includes_warning():
    client = make_client(eval_r=_mock_session_result(count=3))
    result = json.loads(r_check_session(client))
    assert result["rserve_process_count"] == 3
    assert "warning" in result
    assert "pkill" in result["warning"]
    assert "Rserve(args=" in result["warning"]


def test_r_check_session_connection_error_returns_not_connected():
    client = MagicMock()
    client.eval_r.side_effect = RserveConnectionError("refused")
    result = json.loads(r_check_session(client))
    assert result["connected"] is False
    assert "error" in result


# ── r_list_objects ─────────────────────────────────────────────────────────────

def test_r_list_objects_returns_json_array():
    client = make_client(eval_r=["df", "x", "model"])
    result = json.loads(r_list_objects(client))
    assert result == ["df", "x", "model"]


def test_r_list_objects_single_item_normalized():
    """pyRserve returns str for single-element vector; must still be JSON array."""
    client = make_client(eval_r="single_var")
    result = json.loads(r_list_objects(client))
    assert result == ["single_var"]


def test_r_list_objects_empty_env():
    client = make_client(eval_r=None)
    result = json.loads(r_list_objects(client))
    assert result == []


def test_r_list_objects_connection_error_returns_error_json():
    client = MagicMock()
    client.eval_r.side_effect = RserveConnectionError("refused")
    result = json.loads(r_list_objects(client))
    assert "error" in result


def test_r_list_objects_calls_ls():
    client = make_client(eval_r=[])
    r_list_objects(client)
    client.eval_r.assert_called_once_with("ls()")


# ── r_describe_object ──────────────────────────────────────────────────────────

def test_r_describe_object_returns_str_output():
    client = make_client(eval_capture=["'data.frame':\t150 obs.", " $ Sepal.Length: num  5.1 4.9"])
    result = r_describe_object(client, "iris")
    assert "'data.frame'" in result
    assert "Sepal.Length" in result


def test_r_describe_object_calls_str():
    client = make_client(eval_capture=[])
    r_describe_object(client, "iris")
    client.eval_capture.assert_called_once_with("str(iris)")


def test_r_describe_object_eval_error_returns_error_string():
    client = MagicMock()
    client.eval_capture.side_effect = RserveEvalError("object 'xyz' not found")
    result = r_describe_object(client, "xyz")
    assert result.startswith("Error:")


def test_r_describe_object_connection_error_returns_error_string():
    client = MagicMock()
    client.eval_capture.side_effect = RserveConnectionError("refused")
    result = r_describe_object(client, "xyz")
    assert "Connection error:" in result


# ── r_preview_object ───────────────────────────────────────────────────────────

def test_r_preview_object_default_n_10():
    client = make_client(eval_capture=["  a b", "1 1 2"])
    r_preview_object(client, "mydf")
    client.eval_capture.assert_called_once_with("head(mydf, 10)")


def test_r_preview_object_custom_n():
    client = make_client(eval_capture=[])
    r_preview_object(client, "mydf", n=5)
    client.eval_capture.assert_called_once_with("head(mydf, 5)")


def test_r_preview_object_returns_joined_lines():
    client = make_client(eval_capture=["  a b", "1 1 2", "2 3 4"])
    result = r_preview_object(client, "mydf")
    assert result == "  a b\n1 1 2\n2 3 4"


def test_r_preview_object_eval_error_returns_error_string():
    client = MagicMock()
    client.eval_capture.side_effect = RserveEvalError("not found")
    result = r_preview_object(client, "bad")
    assert "Error:" in result


# ── r_summarize_object ─────────────────────────────────────────────────────────

def test_r_summarize_object_calls_summary():
    client = make_client(eval_capture=[])
    r_summarize_object(client, "iris")
    client.eval_capture.assert_called_once_with("summary(iris)")


def test_r_summarize_object_returns_joined_lines():
    client = make_client(eval_capture=["Min. :4.3", "Max. :7.9"])
    result = r_summarize_object(client, "iris")
    assert "Min. :4.3" in result
    assert "Max. :7.9" in result


def test_r_summarize_object_eval_error_returns_error_string():
    client = MagicMock()
    client.eval_capture.side_effect = RserveEvalError("not found")
    result = r_summarize_object(client, "bad")
    assert "Error:" in result


# ── r_get_history ──────────────────────────────────────────────────────────────

def test_r_get_history_returns_json_array():
    client = make_client(eval_r=["x <- 1", "summary(iris)", "plot(x)"])
    result = json.loads(r_get_history(client))
    assert result == ["x <- 1", "summary(iris)", "plot(x)"]


def test_r_get_history_default_n_20_in_expression():
    client = make_client(eval_r=[])
    r_get_history(client)
    expr = client.eval_r.call_args[0][0]
    assert "20" in expr


def test_r_get_history_custom_n_in_expression():
    client = make_client(eval_r=[])
    r_get_history(client, n=50)
    expr = client.eval_r.call_args[0][0]
    assert "50" in expr


def test_r_get_history_empty_returns_empty_array():
    client = make_client(eval_r=None)
    result = json.loads(r_get_history(client))
    assert result == []


def test_r_get_history_connection_error_returns_error_json():
    client = MagicMock()
    client.eval_r.side_effect = RserveConnectionError("refused")
    result = json.loads(r_get_history(client))
    assert "error" in result


def test_r_get_history_expression_reads_rhistory_file():
    """The R expression must reference .Rhistory."""
    client = make_client(eval_r=[])
    r_get_history(client)
    expr = client.eval_r.call_args[0][0]
    assert ".Rhistory" in expr

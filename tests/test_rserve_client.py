from unittest.mock import MagicMock, patch
import pytest
from rstudio_mcp.rserve_client import (
    RserveClient,
    RserveConnectionError,
    RserveEvalError,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def make_mock_conn(eval_return=None):
    conn = MagicMock()
    conn.eval.return_value = eval_return
    conn.r = MagicMock()
    return conn


# ── connect ───────────────────────────────────────────────────────────────────

def test_connect_calls_pyRserve():
    mock_conn = make_mock_conn()
    with patch("pyRserve.connect", return_value=mock_conn) as mock_connect:
        client = RserveClient()
        client.connect()
    mock_connect.assert_called_once_with(host="localhost", port=6311)
    assert client._conn is mock_conn


def test_connect_uses_custom_host_port():
    with patch("pyRserve.connect", return_value=make_mock_conn()) as mock_connect:
        client = RserveClient(host="127.0.0.1", port=9999)
        client.connect()
    mock_connect.assert_called_once_with(host="127.0.0.1", port=9999)


def test_connect_failure_raises_RserveConnectionError():
    with patch("pyRserve.connect", side_effect=ConnectionRefusedError("refused")):
        client = RserveClient()
        with pytest.raises(RserveConnectionError, match="Failed to connect"):
            client.connect()


# ── eval_r ────────────────────────────────────────────────────────────────────

def test_eval_r_returns_value():
    client = RserveClient()
    client._conn = make_mock_conn(eval_return=["a", "b"])
    result = client.eval_r("ls()")
    assert result == ["a", "b"]


def test_eval_r_lazy_connects_when_no_conn():
    mock_conn = make_mock_conn(eval_return=42)
    with patch("pyRserve.connect", return_value=mock_conn):
        client = RserveClient()
        assert client._conn is None
        result = client.eval_r("1 + 1")
    assert result == 42


def test_eval_r_r_error_raises_RserveEvalError():
    import pyRserve.rexceptions as rexc
    client = RserveClient()
    conn = make_mock_conn()
    conn.eval.side_effect = rexc.REvalError("object 'x' not found")
    client._conn = conn
    with pytest.raises(RserveEvalError, match="R evaluation error"):
        client.eval_r("x")


def test_eval_r_connection_drop_resets_conn():
    client = RserveClient()
    conn = make_mock_conn()
    conn.eval.side_effect = OSError("broken pipe")
    client._conn = conn
    with pytest.raises(RserveConnectionError):
        client.eval_r("ls()")
    assert client._conn is None


# ── eval_capture ──────────────────────────────────────────────────────────────

def test_eval_capture_list_return():
    client = RserveClient()
    client._conn = make_mock_conn(eval_return=["line1", "line2"])
    assert client.eval_capture("str(iris)") == ["line1", "line2"]


def test_eval_capture_single_string_return():
    """pyRserve returns str (not list) for single-element character vectors."""
    client = RserveClient()
    client._conn = make_mock_conn(eval_return="only one line")
    assert client.eval_capture("str(x)") == ["only one line"]


def test_eval_capture_none_return():
    """pyRserve returns None for R NULL."""
    client = RserveClient()
    client._conn = make_mock_conn(eval_return=None)
    assert client.eval_capture("invisible(NULL)") == []


def test_eval_capture_wraps_in_capture_output():
    client = RserveClient()
    client._conn = make_mock_conn(eval_return=[])
    client.eval_capture("str(iris)")
    call_expr = client._conn.eval.call_args[0][0]
    assert call_expr.startswith("capture.output(")
    assert "str(iris)" in call_expr


# ── assign_r ──────────────────────────────────────────────────────────────────

def test_assign_r_sets_r_variable():
    client = RserveClient()
    client._conn = make_mock_conn()
    client.assign_r(".__test__", "hello world")
    client._conn.r.__setitem__.assert_called_once_with(".__test__", "hello world")


# ── close ─────────────────────────────────────────────────────────────────────

def test_close_calls_conn_close_and_sets_none():
    client = RserveClient()
    mock_conn = make_mock_conn()
    client._conn = mock_conn
    client.close()
    mock_conn.close.assert_called_once()
    assert client._conn is None


def test_close_when_no_conn_is_noop():
    client = RserveClient()
    client.close()  # should not raise

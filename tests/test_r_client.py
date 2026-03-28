"""Tests for RHttpClient (httpuv backend)."""
import json
from io import BytesIO
from unittest.mock import MagicMock, patch
import urllib.error
import pytest
from rstudio_mcp.r_client import RHttpClient, RserveConnectionError, RserveEvalError


# ── helpers ───────────────────────────────────────────────────────────────────

def _fake_response(payload: dict, status: int = 200):
    """Return a context-manager mock that reads back JSON payload."""
    body = json.dumps(payload).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _urlopen_patch(payload: dict):
    return patch(
        "rstudio_mcp.r_client.urllib.request.urlopen",
        return_value=_fake_response(payload),
    )


# ── constructor / URL ─────────────────────────────────────────────────────────

def test_default_url():
    client = RHttpClient()
    assert client._url == "http://127.0.0.1:6312/mcp"


def test_custom_host_port():
    client = RHttpClient(host="192.168.1.1", port=9999)
    assert client._url == "http://192.168.1.1:9999/mcp"


# ── no-ops ────────────────────────────────────────────────────────────────────

def test_connect_is_noop():
    RHttpClient().connect()  # should not raise


def test_close_is_noop():
    RHttpClient().close()  # should not raise


def test_assign_r_is_noop():
    RHttpClient().assign_r("x", 42)  # should not raise


# ── eval_r ────────────────────────────────────────────────────────────────────

def test_eval_r_returns_decoded_json_value():
    # R server returns value as a JSON string inside {"value": "...", "error": null}
    inner_json = json.dumps([1, 2, 3])
    with _urlopen_patch({"value": inner_json, "error": None}):
        result = RHttpClient().eval_r("c(1, 2, 3)")
    assert result == [1, 2, 3]


def test_eval_r_returns_none_when_value_is_null():
    with _urlopen_patch({"value": None, "error": None}):
        result = RHttpClient().eval_r("invisible(NULL)")
    assert result is None


def test_eval_r_posts_mode_value():
    inner_json = json.dumps(True)
    with patch("rstudio_mcp.r_client.urllib.request.urlopen",
               return_value=_fake_response({"value": inner_json, "error": None})) as mock_open:
        RHttpClient().eval_r("TRUE")
    request_obj = mock_open.call_args[0][0]
    body = json.loads(request_obj.data.decode())
    assert body["mode"] == "value"
    assert body["expression"] == "TRUE"


def test_eval_r_raises_eval_error_on_r_error():
    with _urlopen_patch({"error": "object 'x' not found"}):
        with pytest.raises(RserveEvalError, match="not found"):
            RHttpClient().eval_r("x")


def test_eval_r_raises_connection_error_on_url_error():
    with patch("rstudio_mcp.r_client.urllib.request.urlopen",
               side_effect=urllib.error.URLError("refused")):
        with pytest.raises(RserveConnectionError, match="RStudio session bridge is not running"):
            RHttpClient().eval_r("1 + 1")


# ── eval_capture ──────────────────────────────────────────────────────────────

def test_eval_capture_returns_stdout_lines():
    with _urlopen_patch({"stdout": ["[1] 1", "[1] 2"], "error": None}):
        result = RHttpClient().eval_capture("print(1:2)")
    assert result == ["[1] 1", "[1] 2"]


def test_eval_capture_empty_stdout_returns_empty_list():
    with _urlopen_patch({"stdout": [], "error": None}):
        result = RHttpClient().eval_capture("invisible(NULL)")
    assert result == []


def test_eval_capture_null_stdout_returns_empty_list():
    with _urlopen_patch({"stdout": None, "error": None}):
        result = RHttpClient().eval_capture("invisible(NULL)")
    assert result == []


def test_eval_capture_posts_mode_capture():
    with patch("rstudio_mcp.r_client.urllib.request.urlopen",
               return_value=_fake_response({"stdout": [], "error": None})) as mock_open:
        RHttpClient().eval_capture("str(iris)")
    request_obj = mock_open.call_args[0][0]
    body = json.loads(request_obj.data.decode())
    assert body["mode"] == "capture"
    assert body["expression"] == "str(iris)"


def test_eval_capture_raises_eval_error_on_r_error():
    with _urlopen_patch({"error": "object 'bad' not found"}):
        with pytest.raises(RserveEvalError):
            RHttpClient().eval_capture("bad")


def test_eval_capture_raises_connection_error():
    with patch("rstudio_mcp.r_client.urllib.request.urlopen",
               side_effect=urllib.error.URLError("refused")):
        with pytest.raises(RserveConnectionError, match="rstudio-mcp --print-r-server"):
            RHttpClient().eval_capture("ls()")


def test_connection_error_guidance_mentions_rstudio_console_steps():
    with patch("rstudio_mcp.r_client.urllib.request.urlopen",
               side_effect=urllib.error.URLError("refused")):
        with pytest.raises(RserveConnectionError) as excinfo:
            RHttpClient().eval_r("1 + 1")
    message = str(excinfo.value)
    assert "RStudio Console" in message
    assert "MCP httpuv server started on 127.0.0.1:6312" in message


# ── re-export shim (rserve_client.py) ─────────────────────────────────────────

def test_shim_exports_same_classes():
    from rstudio_mcp.rserve_client import (
        RserveClient,
        RserveConnectionError as ShimConnErr,
        RserveEvalError as ShimEvalErr,
    )
    from rstudio_mcp.r_client import RHttpClient
    assert RserveClient is RHttpClient
    assert ShimConnErr is RserveConnectionError
    assert ShimEvalErr is RserveEvalError

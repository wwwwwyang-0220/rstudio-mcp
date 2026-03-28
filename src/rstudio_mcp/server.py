from __future__ import annotations
import argparse
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from rstudio_mcp.config import ServerConfig
from rstudio_mcp.rserve_client import RserveClient
from rstudio_mcp.tools import session, filesystem, execution

_mcp = FastMCP("RStudio Session Inspector")
_config: ServerConfig = ServerConfig()
_client: RserveClient = RserveClient()


def _setup(config: ServerConfig) -> None:
    global _config, _client
    _config = config
    _client = RserveClient(host=config.host, port=config.port)


@_mcp.tool()
def r_check_session() -> str:
    """Checks the connected R session health.
    Reports PID, R version, working directory, and warns if multiple Rserve
    processes are detected (which would mean MCP is talking to a stale session).
    """
    return session.r_check_session(_client)


@_mcp.tool()
def r_list_objects() -> str:
    """Returns all object names in the R global environment as a JSON array."""
    return session.r_list_objects(_client)


@_mcp.tool()
def r_describe_object(name: str) -> str:
    """Returns structural description of a named R object (type, dimensions, column names)."""
    return session.r_describe_object(_client, name)


@_mcp.tool()
def r_preview_object(name: str, n: int = 10) -> str:
    """Returns first n rows of a named R object. Default n=10."""
    return session.r_preview_object(_client, name, n)


@_mcp.tool()
def r_summarize_object(name: str) -> str:
    """Returns descriptive statistics for a named R object via summary()."""
    return session.r_summarize_object(_client, name)


@_mcp.tool()
def r_get_history(n: int = 20) -> str:
    """Returns last n commands from the R session history as a JSON array."""
    return session.r_get_history(_client, n)


@_mcp.tool()
def r_list_scripts(directory: str) -> str:
    """Lists .R files within an authorized directory."""
    return filesystem.r_list_scripts(_config, _client, directory)


@_mcp.tool()
def r_read_script(path: str) -> str:
    """Returns full text content of an authorized .R file."""
    return filesystem.r_read_script(_config, _client, path)


@_mcp.tool()
def r_execute_code(expression: str) -> str:
    """Executes R expression in .GlobalEnv and returns stdout/stderr as JSON.
    Only available when the server is started with --enable-execution.
    """
    return execution.r_execute_code(_config, _client, expression)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RStudio MCP Server — exposes live R session state to an LLM via MCP."
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Rserve host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6311,
        help="Rserve port (default: 6311)",
    )
    parser.add_argument(
        "--allow-dir",
        action="append",
        dest="allowed_dirs",
        default=[],
        metavar="PATH",
        help="Authorize a directory for .R file access (repeatable)",
    )
    parser.add_argument(
        "--enable-execution",
        action="store_true",
        default=False,
        help="Enable r_execute_code (disabled by default for safety)",
    )
    args = parser.parse_args()

    config = ServerConfig(
        host=args.host,
        port=args.port,
        allowed_dirs=[Path(d) for d in args.allowed_dirs],
        execution_enabled=args.enable_execution,
    )
    _setup(config)
    _mcp.run()


if __name__ == "__main__":
    main()

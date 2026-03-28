# Re-export shim: all code still imports from rstudio_mcp.rserve_client
# but the real implementation has moved to r_client.py (httpuv backend).
from rstudio_mcp.r_client import (  # noqa: F401
    RHttpClient as RserveClient,
    RserveConnectionError,
    RserveEvalError,
)

## Goal

Make `rstudio-mcp` recoverable when the RStudio-side `httpuv` bridge has not been started yet.

## Design

Insert the fallback at the HTTP client boundary in `src/rstudio_mcp/r_client.py`.
Any tool that depends on the RStudio bridge already flows through `RHttpClient`, so this is the narrowest point that can enforce one consistent error message without duplicating logic across tools.

When the POST to `http://127.0.0.1:6312/mcp` fails, raise `RserveConnectionError` with a guided message that tells the user exactly what to do:

1. Run `rstudio-mcp --print-r-server` in a terminal.
2. Paste the printed R code into the RStudio Console.
3. Retry after seeing `MCP httpuv server started on 127.0.0.1:6312`.

`r_check_session` should add a structured `next_step` object alongside `connected: false` so the agent can surface a clearer recovery action than a raw transport failure.

## Scope

This change does not try to auto-run the R bootstrap code. That code must execute inside the currently active RStudio session, so starting a separate R process from Python would connect the wrong environment.

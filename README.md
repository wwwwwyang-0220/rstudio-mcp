# rstudio-mcp

Access your live RStudio session from any MCP-capable client. Inspect objects, preview data, and execute R code directly in the current RStudio environment.

Compatible clients include:

- Codex
- Claude Code
- Claude Desktop

## Installation

**Prerequisites**

- Python 3.11+
- R with `httpuv` and `jsonlite` installed

Install the R dependencies once in RStudio:

```r
install.packages(c("httpuv", "jsonlite"))
```

Install the CLI with `pipx`:

```bash
pipx install /path/to/rstudio-mcp
```

Then verify the command is available:

```bash
rstudio-mcp --help
```

## Configure an MCP client

This is a local `stdio` MCP server, not a remote HTTP/SaaS MCP.

### Codex

```bash
codex mcp add rstudio -- rstudio-mcp --enable-execution
```

Codex stores this in `~/.codex/config.toml`, shared by the CLI and app/IDE clients.

### Claude Code

```bash
claude mcp add rstudio -- rstudio-mcp --enable-execution
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rstudio": {
      "command": "/path/to/bin/rstudio-mcp",
      "args": ["--enable-execution"]
    }
  }
}
```

`--enable-execution` enables code execution through `r_execute_code`. It is off by default.

## Usage

Recommended setup: install automatic startup once:

```bash
rstudio-mcp --install-auto-start
```

This command:

- writes `~/.rstudio-mcp/bootstrap.R`
- ensures your `~/.Rprofile` sources that bootstrap file

After that, each new interactive RStudio session will automatically start the local bridge when possible.

If you prefer a one-off manual startup instead, run this once in a terminal for the current RStudio session:

```bash
rstudio-mcp --print-r-server
```

Paste the printed R code into the RStudio Console and execute it. When you see:

```text
MCP httpuv server started on 127.0.0.1:6312
```

the connection is ready.

You can then interact with the R session from Codex or Claude using natural language, for example:

- *"List all objects in the current environment"*
- *"Preview the data frame `df`"*
- *"Add a new column to `df` filled with 0"*

To remove the `.Rprofile` hook later:

```bash
rstudio-mcp --uninstall-auto-start
```

The bridge will normally stop when you restart the R session, explicitly run `rm(list = ls(all.names = TRUE))`, or manually stop the server.

## What happens if you forget to start the RStudio bridge

If you forget to start the RStudio-side bridge, the MCP checks at runtime whether `httpuv` is reachable.

If it cannot connect to `127.0.0.1:6312`, it returns a recovery message telling you to:

1. Run `rstudio-mcp --print-r-server`
2. Paste the printed R code into the RStudio Console
3. Retry after RStudio shows `MCP httpuv server started on 127.0.0.1:6312`

You do not need to remember this setup step manually anymore.

## Available tools

| Tool | Description |
|------|------|
| `r_check_session` | Check session status, including PID, R version, and working directory |
| `r_list_objects` | List all objects in the global environment |
| `r_describe_object` | Inspect an object's structure, type, dimensions, and columns |
| `r_preview_object` | Preview the first N rows of an object |
| `r_summarize_object` | Return descriptive statistics via `summary()` |
| `r_get_history` | Read recent command history |
| `r_list_scripts` | List `.R` files in a directory |
| `r_read_script` | Read an `.R` script |
| `r_execute_code` | Execute R code when `--enable-execution` is enabled |

## CLI options

```text
--host              httpuv host (default: 127.0.0.1)
--port              httpuv port (default: 6312)
--allow-dir PATH    Authorize a directory for `.R` file access; repeatable
--enable-execution  Enable the `r_execute_code` tool
--install-auto-start
                    Install or update the per-user RStudio auto-start bootstrap
--uninstall-auto-start
                    Remove the auto-start snippet from `~/.Rprofile`
--print-r-server    Print the R bootstrap script and exit
```

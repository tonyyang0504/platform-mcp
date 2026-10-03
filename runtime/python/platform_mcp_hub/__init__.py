"""platform-mcp-hub: MCP servers for platform APIs, from one catalog (Python runtime).

One package holds the runtime, the whole catalog and a CLI (``platform-mcp-hub list|describe|serve|directory``).
A served catalog entry (the *spec*) is interpreted by ``build_server(spec)``: credential resolution,
HTTP with client-side rate limiting, error mapping to ``isError`` results, category verb vocabularies
with their input/output schemas, and tool registration with the annotations the MCP standard expects.
The TypeScript runtime (npm ``platform-mcp-hub``) implements the same contract from the same catalog.

Imports are lazy so the catalog tools (lint, catalog lookups) work without loading the MCP SDK."""

__version__ = "0.1.0"
__all__ = ["build_server", "main", "run_http", "run_stdio", "__version__"]


def __getattr__(name: str):
    if name in ("build_server", "main", "run_http", "run_stdio"):
        from . import server
        return getattr(server, name)
    raise AttributeError(f"module 'platform_mcp_hub' has no attribute {name!r}")

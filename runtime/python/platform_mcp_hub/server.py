"""Build an MCPServer from a catalog entry: one tool per mapped verb, with the vocabulary's
schemas and the annotations the standard expects, structured output, and ``isError`` results."""

import asyncio
import inspect
import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from . import credentials, environment
from .sanitize import clean
from .adapter import Adapter
from .errors import PlatformError
from .http import Transport
from .vocab import vocab_for


def _tool_result(payload: dict, is_error: bool = False) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, default=str))], structured_content=payload, is_error=is_error)


def build_server(spec: dict, *, transport: Transport | None = None) -> MCPServer:
    pid = spec["id"]
    category = spec["category"]
    vocab = vocab_for(spec)
    adapter_spec = spec["adapter"]
    creds: dict[str, str] = {}
    # catalog text is cleaned before a client's model reads it (sanitize.py): an entry may come from a hostile document
    label = clean(spec.get("label") or pid, "label")
    generic = category == "generic"
    server = MCPServer(
        name=f"{pid}-mcp",
        title=label if generic else f"{label} ({category})",
        version=spec.get("version", "0.1.0"),
        instructions=clean(spec.get("instructions"), "instructions") or ((
            f"Tools for the {label} API. Every tool maps to an endpoint documented at "
            f"{clean(spec.get('docs_url'), 'instructions')}. Results are the API's own answer under `data`; "
            "read tools take `select_fields` to return only some fields.") if generic else (
            f"Tools for {label}, a {category.replace('_', ' ')} platform. "
            "Every tool maps to an endpoint documented on the platform's developer pages "
            f"({clean(spec.get('docs_url'), 'instructions')}). Results carry a normalised shape plus the raw record under `raw`.")
        ),
    )
    state: dict[str, Any] = {"transport": transport, "adapter": None}

    def adapter() -> Adapter:
        if state["adapter"] is None:
            # PLATFORM_MCP_<ID>_ENV / _BASE_URL (environment.py): an injected transport keeps its own base URL
            eff, env = environment.select(pid, adapter_spec)
            if state["transport"] is None:
                creds.update(credentials.resolve(pid, eff.get("auth", {"type": "none", "fields": []}), eff.get("config_fields")))
                ua = f"platform-mcp/{pid} (+https://github.com/tonyyang0504/platform-mcp)"
                if eff.get("user_agent_field") and creds.get(eff["user_agent_field"]):
                    ua = f"{ua} {creds[eff['user_agent_field']]}"  # SEC-style operator contact
                state["transport"] = Transport(
                    eff["base_url"], {**eff.get("auth", {"type": "none"}), "state_key": environment.state_key(pid, env)}, creds,
                    float(eff.get("rate_per_second", 2)), ua, envelope=eff.get("envelope"),
                )
            state["transport"].fixed_headers = eff.get("headers") or {}
            if eff.get("error_kinds"):
                state["transport"].error_kinds = eff["error_kinds"]  # per-entry overrides of the error table
            state["environment"] = env
            state["adapter"] = Adapter({**spec, "adapter": eff}, state["transport"])
        return state["adapter"]

    for verb, tool_spec in adapter_spec["tools"].items():
        v = vocab[verb]

        def make(verb=verb, v=v):
            async def handler(**kwargs: Any) -> CallToolResult:
                try:
                    payload = await adapter().call(verb, kwargs)
                    return _tool_result(payload)
                except PlatformError as exc:
                    return _tool_result(exc.payload(), is_error=True)
                except Exception as exc:  # never leak a traceback with secrets
                    return _tool_result({"error": "internal_error", "message": credentials.scrub(f"{exc.__class__.__name__}: {exc}")[:300]}, is_error=True)
            return handler

        fn = make()
        fn.__name__ = verb
        fn.__doc__ = v["description"]
        # the SDK builds the argument model from the signature: give it the vocabulary's inputs
        props = v["input"].get("properties", {})
        required = set(v["input"].get("required", []))
        fn.__signature__ = inspect.Signature([
            inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=inspect.Parameter.empty if name in required else None, annotation=Any)
            for name in props
        ])
        fn.__annotations__ = {name: Any for name in props}
        server.add_tool(
            fn, name=verb, title=v["title"], description=v["description"] + (f" {clean(tool_spec['note'], 'note')}" if tool_spec.get("note") else ""),
            annotations=ToolAnnotations(title=v["title"], read_only_hint=v.get("read_only", False), destructive_hint=v.get("destructive", not v.get("read_only", False)),
                                        idempotent_hint=v.get("idempotent", v.get("read_only", False)), open_world_hint=True),
            structured_output=False,
        )
        # the vocabulary schemas are the contract (the SDK would otherwise infer from **kwargs)
        tool = server._tool_manager.get_tool(verb)
        tool.parameters = v["input"]
        tool.fn_metadata.output_schema = v["output"]
        tool.meta = {"platform_mcp/endpoint": tool_spec.get("path"), "platform_mcp/docs": tool_spec.get("docs") or spec.get("docs_url"), "platform_mcp/verified_at": spec.get("verified_at")}
    return server


def run_stdio(spec: dict) -> None:
    server = build_server(spec)
    asyncio.run(server.run_stdio_async())


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
TOKEN_ENV = "PLATFORM_MCP_HTTP_TOKEN"
MIN_TOKEN = 24


def http_auth_token(host: str, allow_remote: bool, environ: dict | None = None) -> str | None:
    """The bearer token every HTTP request must carry, or None (loopback without a token). A server acts with the
    operator's credentials, so a non-loopback bind needs BOTH --allow-remote and PLATFORM_MCP_HTTP_TOKEN; otherwise
    ValueError (the message never repeats the token). The TypeScript runtime's httpAuthToken is identical."""
    import os
    env = os.environ if environ is None else environ
    token = (env.get(TOKEN_ENV) or "").strip() or None
    if token is not None and len(token) < MIN_TOKEN:
        raise ValueError(f"{TOKEN_ENV} must be at least {MIN_TOKEN} characters (a random secret)")
    if host not in LOOPBACK_HOSTS and not (allow_remote and token):
        raise ValueError(f"refusing to serve HTTP on {host!r}: the server acts with the operator's credentials. Bind 127.0.0.1, "
                         f"or pass --allow-remote AND set {TOKEN_ENV} (clients send 'Authorization: Bearer <token>')")
    return token


class BearerAuth:
    """ASGI middleware: every HTTP request needs `Authorization: Bearer <token>` (constant-time comparison)."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            import hmac
            got = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not (got[:7].lower() == b"bearer " and hmac.compare_digest(got[7:].strip(), self.token)):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"www-authenticate", b'Bearer realm="platform-mcp"'), (b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error": "unauthorized"}'})
                return
        await self.app(scope, receive, send)


def http_app(spec: dict, host: str = "127.0.0.1", token: str | None = None):
    """The Streamable HTTP ASGI app (stateless, one /mcp endpoint), behind the bearer check when a token is set."""
    app = build_server(spec).streamable_http_app(stateless_http=True, host=host)
    return BearerAuth(app, token) if token else app


def _serve(app, host: str, port: int) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")


def run_http(spec: dict, host: str = "127.0.0.1", port: int = 8000, allow_remote: bool = False) -> None:
    """Streamable HTTP, stateless (no session ids), JSON-RPC over a single /mcp endpoint."""
    token = http_auth_token(host, allow_remote)
    _serve(http_app(spec, host, token), host, port)


def main(spec: dict, argv: list[str] | None = None) -> None:
    import argparse
    import sys
    ap = argparse.ArgumentParser(description=f"{spec.get('label') or spec['id']} MCP server")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--allow-remote", action="store_true", help=f"allow a non-loopback --host (also requires {TOKEN_ENV})")
    args = ap.parse_args(argv)
    if args.http:
        try:
            run_http(spec, args.host, args.port, args.allow_remote)
        except ValueError as exc:
            print(f"platform-mcp: {exc}", file=sys.stderr)
            raise SystemExit(2)
    else:
        run_stdio(spec)

"""Installed-package smoke: start each command over stdio, initialize, list tools, call the first tool.
Usage: python tools/smoke_stdio.py "<command> [args]" ["<command> [args]" ...]
e.g.   python tools/smoke_stdio.py "platform-mcp-hub serve reed" "npx platform-mcp-hub directory"
(needs the `mcp` client in the running interpreter; no credentials: a tool that needs them answers a clean isError)."""
import asyncio
import os
import shlex
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def check(cmdline: str) -> None:
    cmd, *args = shlex.split(cmdline)
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}
    async with stdio_client(StdioServerParameters(command=cmd, args=args, env=env)) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            assert tools, f"{cmdline}: no tools"
            first = tools[0]
            call_args = {k: "x" for k in (first.input_schema.get("required") or [])}
            res = await s.call_tool(first.name, call_args)
            assert res.content, f"{cmdline}: empty result"
            print(f"ok {cmdline}: {init.server_info.name} proto={init.protocol_version} tools={[t.name for t in tools]} first_call_is_error={res.is_error}")


async def main() -> None:
    for cmdline in sys.argv[1:]:
        await check(cmdline)


asyncio.run(main())

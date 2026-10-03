# 사람인 Saramin MCP server

Category: **jobs** · Docs: https://oapi.saramin.co.kr/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/saramin.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /job-search` (https://oapi.saramin.co.kr/guide/job-search)
- ~~`me`~~ not offered: No account endpoint; the access-key is the only credential.
- ~~`get_posting`~~ not offered: The guide documents only the job-search operation (no per-id detail call); each hit's url is the Saramin posting page.
- ~~`apply`~~ not offered: No application endpoint; applicants apply on saramin.co.kr.
- ~~`list_messages`~~ not offered: No messaging API is documented.

## Credentials

- `PLATFORM_MCP_SARAMIN_ACCESS_KEY` — access-key issued after Saramin approves your API application (이용신청) and you register an app at https://oapi.saramin.co.kr/.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve saramin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve saramin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve saramin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/saramin-mcp`. Python and TypeScript serve identical tools.

# Freelancer.com MCP server

Category: **jobs** · Docs: https://developers.freelancer.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/freelancer_com.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /projects/0.1/projects/active/` (https://developers.freelancer.com/docs/projects/projects#projects-get-3)
- `get_posting` — `GET /projects/0.1/projects/{id}/` (https://developers.freelancer.com/docs/projects/projects#projects-get-2)
- `list_messages` — `GET /messages/0.1/messages/` (https://developers.freelancer.com/docs/messaging/messaging#messages-get)
- ~~`me`~~ not offered: Served by the Freelancer deals server (GET /users/0.1/self/); the jobs vocabulary keeps this entry to project discovery.
- ~~`apply`~~ not offered: A Freelancer 'application' is a bid (POST /projects/0.1/bids/) that needs amount, period and milestone_percentage, which the jobs apply input (cover_letter, resume_url) does not carry — use the freelancer deals server's submit_bid.

## Credentials

- `PLATFORM_MCP_FREELANCER_COM_ACCESS_TOKEN` — Freelancer OAuth access token sent as the freelancer-oauth-v1 header: a Personal Access Token from https://accounts.freelancer.com/settings/develop ('valid for thirty days') or a token from your registered OAuth app.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve freelancer_com   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve freelancer_com
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve freelancer_com   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/freelancer_com-mcp`. Python and TypeScript serve identical tools.

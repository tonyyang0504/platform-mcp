# Resend MCP server

Category: **messaging** · Docs: https://resend.com/docs · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/resend.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api-keys` (https://resend.com/docs/api-reference/api-keys/list-api-keys)
- `send` — `POST /emails` (https://resend.com/docs/api-reference/emails/send-email)
- `list_inbound` — `GET /emails/receiving` (https://resend.com/docs/api-reference/emails/list-received-emails)
- ~~`reply`~~ not offered: Threading on POST /emails goes through a nested `headers` object (In-Reply-To / References), which the adapter's flat body map cannot express (https://resend.com/docs/api-reference/emails/send-email).
- ~~`get_thread`~~ not offered: GET /emails/receiving/{id} returns one received email, not a conversation; no thread listing is documented (https://resend.com/docs/api-reference/emails/retrieve-received-email).
- ~~`mark_read`~~ not offered: No read-state endpoint exists in the Resend API (https://resend.com/docs/api-reference/introduction).

## Credentials

- `PLATFORM_MCP_RESEND_API_KEY` — Resend team API key (re_…), sent as 'Authorization: Bearer re_xxxxxxxxx' (https://resend.com/docs/api-reference/introduction).
- `PLATFORM_MCP_RESEND_SENDER` — Verified-domain sender address used as `from` on every send ('Sender email address', 'Name <email@domain>' allowed; https://resend.com/docs/api-reference/emails/send-email). Env: PLATFORM_MCP_RESEND_SENDER.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve resend   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve resend
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve resend   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/resend-mcp`. Python and TypeScript serve identical tools.

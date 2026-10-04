# Postmark MCP server

Category: **messaging** · Docs: https://postmarkapp.com/developer · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/postmark.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /server` (https://postmarkapp.com/developer/api/server-api)
- `send` — `POST /email` (https://postmarkapp.com/developer/api/email-api)
- `list_inbound` — `GET /messages/inbound` (https://postmarkapp.com/developer/api/messages-api)
- ~~`reply`~~ not offered: Threading on POST /email needs Headers[{Name, Value}] (In-Reply-To / References), an array the adapter's flat body map cannot express (https://postmarkapp.com/developer/api/email-api).
- ~~`get_thread`~~ not offered: GET /messages/inbound/{messageid}/details returns one message, not a conversation; no thread listing is documented (https://postmarkapp.com/developer/api/messages-api).
- ~~`mark_read`~~ not offered: No read-state endpoint exists in the Postmark API (https://postmarkapp.com/developer/api/overview).

## Credentials

- `PLATFORM_MCP_POSTMARK_SERVER_TOKEN` — Postmark server API token, sent as the X-Postmark-Server-Token header ('requests that require server level privileges'; 401 'Missing or incorrect API token in header', https://postmarkapp.com/developer/api/overview).
- `PLATFORM_MCP_POSTMARK_SENDER` — Sender address used as `From` on every send: 'Sender email address. Registered and confirmed Sender Signature is required' (https://postmarkapp.com/developer/api/email-api). Env: PLATFORM_MCP_POSTMARK_SENDER.
- `PLATFORM_MCP_POSTMARK_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_POSTMARK_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve postmark          # Python
    npx -y platform-mcp-hub serve postmark       # TypeScript
    claude mcp add postmark -- uvx platform-mcp-hub serve postmark

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/postmark-mcp`. Python and TypeScript serve identical tools.

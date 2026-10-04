# SendGrid MCP server

Category: **messaging** · Docs: https://www.twilio.com/docs/sendgrid · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/sendgrid.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user/account` (https://www.twilio.com/docs/sendgrid/api-reference/users-api/get-a-users-account-information)
- `send` — `POST /mail/send` (https://www.twilio.com/docs/sendgrid/api-reference/mail-send/mail-send)
- ~~`list_inbound`~~ not offered: Inbound mail is delivered by the Inbound Parse Webhook (an MX record on a subdomain and a multipart POST to the customer's server), not by a pollable endpoint; the Email Activity API (GET /v3/messages) is a paid add-on with a required query-language parameter (https://www.twilio.com/docs/sendgrid/for-developers/parsing-email/setting-up-the-inbound-parse-webhook).
- ~~`get_thread`~~ not offered: SendGrid has no conversation or thread resource; sent mail is only queryable through the paid Email Activity API (https://www.twilio.com/docs/sendgrid/api-reference/mail-send/mail-send).
- ~~`reply`~~ not offered: A reply would be a new mail/send with In-Reply-To / References headers, but the vocabulary's reply input carries no recipient address and SendGrid has no thread id to resolve one from (https://www.twilio.com/docs/sendgrid/api-reference/mail-send/mail-send).
- ~~`mark_read`~~ not offered: No read-state endpoint exists in the SendGrid v3 API (https://www.twilio.com/docs/sendgrid/api-reference).

## Credentials

- `PLATFORM_MCP_SENDGRID_API_KEY` — SendGrid API key with Mail Send (and, for `me`, User Account read) permission, sent as 'Authorization: Bearer <API key>' ('add an HTTP Authorization header to your API request that contains an API Key', https://www.twilio.com/docs/sendgrid/api-reference/how-to-use-the-sendgrid-v3-api/authentication). EU-pinned accounts live on https://api.eu.sendgrid.com, which this server does not switch to.
- `PLATFORM_MCP_SENDGRID_SENDER` — Verified sender address used as `from.email` on every send ('from (object with required email field)' — a verified Sender Identity or authenticated domain is required, https://www.twilio.com/docs/sendgrid/api-reference/mail-send/mail-send). Env: PLATFORM_MCP_SENDGRID_SENDER.
- `PLATFORM_MCP_SENDGRID_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_SENDGRID_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve sendgrid          # Python
    npx -y platform-mcp-hub serve sendgrid       # TypeScript
    claude mcp add sendgrid -- uvx platform-mcp-hub serve sendgrid

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/sendgrid-mcp`. Python and TypeScript serve identical tools.

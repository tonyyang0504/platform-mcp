# Bundesagentur für Arbeit Jobsuche MCP server

Category: **jobs** · Docs: https://jobsuche.api.bund.dev/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/arbeitsagentur.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /pc/v6/jobs` (https://jobsuche.api.bund.dev/)
- `get_posting` — `GET /pc/v4/jobdetails/{id}` (https://jobsuche.api.bund.dev/)
- ~~`me`~~ not offered: No account endpoint: the X-API-Key is the fixed public client id 'jobboerse-jobsuche', not a personal credential, and the OpenAPI lists only job search, job details and employer logo.
- ~~`apply`~~ not offered: Page: 'applications to the employer' — the OpenAPI documents no application endpoint; candidates apply on arbeitsagentur.de or the employer site.
- ~~`list_messages`~~ not offered: No messaging API; the OpenAPI documents job search, job details and the employer logo only.

## Credentials

- `PLATFORM_MCP_ARBEITSAGENTUR_API_KEY` — The fixed public client id from https://jobsuche.api.bund.dev/ ('X-API-Key ist die clientId jobboerse-jobsuche'): set PLATFORM_MCP_ARBEITSAGENTUR_API_KEY=jobboerse-jobsuche. No registration exists; the BA publishes no developer terms of its own.

## Run

    uvx platform-mcp-hub serve arbeitsagentur          # Python
    npx -y platform-mcp-hub serve arbeitsagentur       # TypeScript
    claude mcp add arbeitsagentur -- uvx platform-mcp-hub serve arbeitsagentur

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arbeitsagentur-mcp`. Python and TypeScript serve identical tools.

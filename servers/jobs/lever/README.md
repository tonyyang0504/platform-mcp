# Lever MCP server

Category: **jobs** · Docs: https://github.com/lever/postings-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/lever.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /{site}` (https://github.com/lever/postings-api#get-a-list-of-job-postings)
- `get_posting` — `GET /{site}/{id}` (https://github.com/lever/postings-api#get-a-specific-job-posting)
- ~~`me`~~ not offered: The postings endpoints are public and keyless; there is no account endpoint to verify.
- ~~`apply`~~ not offered: POST /v0/postings/SITE/POSTING-ID?key=APIKEY needs 'an API key, which a Super Admin of your account can generate' (the employer's key) and 'our API only accepts resumes in multipart form data mode'; candidates apply at the posting's applyUrl (Lever's hosted form).
- ~~`list_messages`~~ not offered: The Postings API only lists postings and accepts applications; it has no messaging endpoints.

## Credentials

- `PLATFORM_MCP_LEVER_SITE` — The company's Lever site name (usually the company name without spaces), e.g. 'leverdemo' in https://jobs.lever.co/leverdemo.
- `PLATFORM_MCP_LEVER_API_HOST` — Lever postings host for the site's instance: api.lever.co (global) or api.eu.lever.co (EU).

## Run

    uvx platform-mcp-hub serve lever          # Python
    npx -y platform-mcp-hub serve lever       # TypeScript
    claude mcp add lever -- uvx platform-mcp-hub serve lever

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lever-mcp`. Python and TypeScript serve identical tools.

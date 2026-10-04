# Teamtailor MCP server

Category: **jobs** · Docs: https://docs.teamtailor.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/teamtailor.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /jobs` (https://docs.teamtailor.com/#authentication)
- `search` — `GET /jobs` (https://docs.teamtailor.com/#jobs)
- `get_posting` — `GET /jobs/{id}` (https://docs.teamtailor.com/#jobs)
- ~~`apply`~~ not offered: POST /v1/job-applications (Create job application) needs an Admin-scope key ('Can create new jobs, candidates and job applications'), i.e. the employer's credential; candidates apply via links.careersite-job-apply-url.
- ~~`list_messages`~~ not offered: The API reference (Postman collection behind https://docs.teamtailor.com/) has no messages or conversations resource.

## Credentials

- `PLATFORM_MCP_TEAMTAILOR_API_KEY` — Teamtailor API key with the Public scope (read), created at https://app.teamtailor.com/app/settings/integrations/api-keys; sent as `Authorization: Token token=<key>`.
- `PLATFORM_MCP_TEAMTAILOR_API_HOST` — Teamtailor API host for the account's data stack: api.teamtailor.com (EU stack) or api.na.teamtailor.com (NA stack).

## Run

    uvx platform-mcp-hub serve teamtailor          # Python
    npx -y platform-mcp-hub serve teamtailor       # TypeScript
    claude mcp add teamtailor -- uvx platform-mcp-hub serve teamtailor

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/teamtailor-mcp`. Python and TypeScript serve identical tools.

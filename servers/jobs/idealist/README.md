# Idealist MCP server

Category: **jobs** · Docs: https://api-sandbox.idealist.org/listings-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/idealist.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /listings/jobs` (https://api-sandbox.idealist.org/listings-api#authentication)
- `search` — `GET /listings/jobs` (https://api-sandbox.idealist.org/listings-api#jobs)
- `get_posting` — `GET /listings/jobs/{id}` (https://api-sandbox.idealist.org/listings-api#job-details)
- ~~`apply`~~ not offered: The Apply API only creates applications for volunteer listings ('create listing applications for volunteer listings', POST https://www.idealist.org/api/v1/listings/volops/{volop_id}/apply, https://api-sandbox.idealist.org/apply-api); jobs are applied to through the job's applyUrl / applyEmail.
- ~~`list_messages`~~ not offered: No messaging endpoint; the Listings API covers jobs, internships and volunteer listings only.

## Credentials

- `PLATFORM_MCP_IDEALIST_API_KEY` — Idealist Listings API key; 'API keys are issued manually. Contact support@idealist.org to request a production key.' Sent as the Basic-auth username with an empty password.

## Run

    uvx platform-mcp-hub serve idealist          # Python
    npx -y platform-mcp-hub serve idealist       # TypeScript
    claude mcp add idealist -- uvx platform-mcp-hub serve idealist

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/idealist-mcp`. Python and TypeScript serve identical tools.

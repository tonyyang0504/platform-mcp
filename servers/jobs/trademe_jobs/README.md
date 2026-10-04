# Trade Me Jobs MCP server

Category: **jobs** · Docs: https://developer.trademe.co.nz/api-reference/search-methods/jobs-search/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/trademe_jobs.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /MyTradeMe/Summary.json` (https://developer.trademe.co.nz/api-reference/my-trade-me-methods/retrieve-your-profile-information/)
- `search` — `GET /Search/Jobs.json` (https://developer.trademe.co.nz/api-reference/search-methods/jobs-search/)
- `get_posting` — `GET /Listings/{id}.json` (https://developer.trademe.co.nz/api-reference/listing-methods/retrieve-the-details-of-a-single-listing/)
- ~~`apply`~~ not offered: The listing detail exposes HasAppliedForJob / JobApplicationDate only; the API reference documents no job-application method.
- ~~`list_messages`~~ not offered: The Trade Me API reference documents no member-messaging method for job listings.

## Credentials

- `PLATFORM_MCP_TRADEME_JOBS_CONSUMER_KEY` — Trade Me application consumer key (My Trade Me > My applications).
- `PLATFORM_MCP_TRADEME_JOBS_CONSUMER_SECRET` — Trade Me application consumer secret.
- `PLATFORM_MCP_TRADEME_JOBS_OAUTH_TOKEN` — Member access token from the OAuth 1.0a flow (Trade Me access tokens do not expire).
- `PLATFORM_MCP_TRADEME_JOBS_OAUTH_TOKEN_SECRET` — Access token secret from the same flow.

## Run

    uvx platform-mcp-hub serve trademe_jobs          # Python
    npx -y platform-mcp-hub serve trademe_jobs       # TypeScript
    claude mcp add trademe_jobs -- uvx platform-mcp-hub serve trademe_jobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/trademe_jobs-mcp`. Python and TypeScript serve identical tools.

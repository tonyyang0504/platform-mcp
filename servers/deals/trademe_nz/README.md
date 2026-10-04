# Trade Me Jobs MCP server

Category: **deals** · Docs: https://developer.trademe.co.nz/api-reference/search-methods/jobs-search · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/trademe_nz.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /Search/Jobs.json` (https://developer.trademe.co.nz/api-reference/search-methods/jobs-search)
- `get_posting` — `GET /Listings/{id}.json` (https://developer.trademe.co.nz/api-reference/listing-methods/retrieve-the-details-of-a-single-listing)
- ~~`me`~~ not offered: Member endpoints (/v1/MyTradeMe/Summary) need a member access token from the OAuth 1.0a RequestToken → Authorize → AccessToken flow; this adapter signs as the application only.
- ~~`submit_bid`~~ not offered: Job applications are made on Trade Me (Apply Online); Trade Me's bidding API applies to auctions, not job listings.
- ~~`withdraw_bid`~~ not offered: No job-application API (see submit_bid).
- ~~`bid_status`~~ not offered: No job-application API (see submit_bid).
- ~~`list_messages`~~ not offered: Member messaging needs a member token (not offered by this application-signed adapter).
- ~~`send_message`~~ not offered: Asking an employer a question needs a member token (not offered by this application-signed adapter).
- ~~`credits`~~ not offered: No credit balance for job seekers.

## Credentials

- `PLATFORM_MCP_TRADEME_NZ_CONSUMER_KEY` — Trade Me API consumer key of your registered application (My Trade Me → Developer options; API access is granted after Trade Me reviews the application).
- `PLATFORM_MCP_TRADEME_NZ_CONSUMER_SECRET` — The application's consumer secret: sent as the OAuth 1.0a PLAINTEXT signature '<consumer secret>&' over HTTPS (Trade Me's documented PLAINTEXT workflow).

## Run

    uvx platform-mcp-hub serve deals/trademe_nz          # Python
    npx -y platform-mcp-hub serve deals/trademe_nz       # TypeScript
    claude mcp add trademe_nz -- uvx platform-mcp-hub serve deals/trademe_nz

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/trademe_nz-deals-mcp`. Python and TypeScript serve identical tools.

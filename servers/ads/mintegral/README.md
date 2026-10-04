# Mintegral MCP server

Category: **ads** · Docs: https://adv-new.mintegral.com/doc/en/guide/introduction/quickStart.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/mintegral.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/open/v1/account/balance` (https://adv-new.mintegral.com/doc/en/guide/account/getAccountBalance.html)
- `list_accounts` — `GET /api/open/v1/account/balance` (https://adv-new.mintegral.com/doc/en/guide/account/getAccountBalance.html)
- `list_campaigns` — `GET /api/open/v1/offers` (https://adv-new.mintegral.com/doc/en/guide/offer/getOffer.html)
- `update_budget` — `PUT /api/open/v1/offer/budget` (https://adv-new.mintegral.com/doc/en/guide/offer/updateBudget.html)
- `pause_resume` — `PUT /api/open/v1/offer/status` (https://adv-new.mintegral.com/doc/en/guide/offer/updateStatus.html)
- ~~`get_report`~~ not offered: The only performance report is asynchronous and returns a file: 'Calling this interface is divided into two steps: First you need to set the parameter type = 1 … The system will generate data asynchronously … After the data is generated, set the parameter type = 2 … will directly return the file byte stream (Content-Type: application / octet-stream) … separated by "\t" as columns' (https://adv-new.mintegral.com/doc/en/guide/report/advancedPerformanceReport.html).

## Credentials

- `PLATFORM_MCP_MINTEGRAL_ACCESS_KEY` — Access Key from Mintegral AppGrowth > Account Management > Basic Information; sent as the access-key header of every Open API call.
- `PLATFORM_MCP_MINTEGRAL_API_KEY` — API Key from the same Basic Information page; never sent, only used to compute the per-request token = md5(api_key + md5(timestamp)).

## Run

    uvx platform-mcp-hub serve mintegral          # Python
    npx -y platform-mcp-hub serve mintegral       # TypeScript
    claude mcp add mintegral -- uvx platform-mcp-hub serve mintegral

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mintegral-mcp`. Python and TypeScript serve identical tools.

# Upwork MCP server

Category: **deals** · Docs: https://www.upwork.com/developer/documentation/graphql/api/docs/index.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/upwork.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#query-user)
- `search_postings` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#query-marketplaceJobPostingsSearch)
- `get_posting` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#query-marketplaceJobPosting)
- `bid_status` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#query-vendorProposal)
- `list_messages` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#query-roomStories)
- `send_message` — `POST /graphql` (https://www.upwork.com/developer/documentation/graphql/api/docs/index.html#mutation-createRoomStoryV2)
- ~~`submit_bid`~~ not offered: The GraphQL reference documents no mutation that submits a freelancer proposal (only clientProposals/messageClientProposal for clients and vendorProposals reads); proposals are submitted on upwork.com.
- ~~`withdraw_bid`~~ not offered: No mutation to withdraw a vendor proposal is documented.
- ~~`credits`~~ not offered: Connects balance is not exposed by a documented query.

## Credentials

- `PLATFORM_MCP_UPWORK_CLIENT_ID` — Client ID of an approved Upwork API key (apply at https://www.upwork.com/developer/keys/apply; Upwork reviews every key).
- `PLATFORM_MCP_UPWORK_CLIENT_SECRET` — Client secret of the same API key (form body of the refresh_token grant).
- `PLATFORM_MCP_UPWORK_REFRESH_TOKEN` — Refresh token from the Authorization Code Grant for the freelancer/agency account; the runtime mints access tokens (TTL 86400 s) at https://www.upwork.com/api/v3/oauth2/token and keeps the rotated refresh_token each response returns (set PLATFORM_MCP_STATE_DIR to persist it).
- `PLATFORM_MCP_UPWORK_TENANT_ID` — Optional organization id sent as X-Upwork-API-TenantId (the execution context; without it the user's default organization is used).

## Run

    uvx platform-mcp-hub serve upwork          # Python
    npx -y platform-mcp-hub serve upwork       # TypeScript
    claude mcp add upwork -- uvx platform-mcp-hub serve upwork

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/upwork-mcp`. Python and TypeScript serve identical tools.

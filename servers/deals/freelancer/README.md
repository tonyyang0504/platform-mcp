# Freelancer MCP server

Category: **deals** · Docs: https://developers.freelancer.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/freelancer.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/0.1/self/` (https://developers.freelancer.com/docs/users/authenticated-users#logged-in-user-get)
- `search_postings` — `GET /projects/0.1/projects/active/` (https://developers.freelancer.com/docs/projects/projects#projects-get-3)
- `get_posting` — `GET /projects/0.1/projects/{id}/` (https://developers.freelancer.com/docs/projects/projects#projects-get-2)
- `submit_bid` — `POST /projects/0.1/bids/` (https://developers.freelancer.com/docs/projects/bids#bids-post)
- `withdraw_bid` — `PUT /projects/0.1/bids/{bid_id}/` (https://developers.freelancer.com/docs/projects/bids#bids-put-1)
- `bid_status` — `GET /projects/0.1/bids/{bid_id}/` (https://developers.freelancer.com/docs/projects/bids#bids-get-1)
- `list_messages` — `GET /messages/0.1/messages/` (https://developers.freelancer.com/docs/messaging/messaging#messages-get)
- `send_message` — `POST /messages/0.1/threads/{thread_id}/messages/` (https://developers.freelancer.com/docs/messaging/threads#threads-post-2)
- ~~`credits`~~ not offered: The API documents no bid-credit endpoint; the account balance (users/self balance_details) is money, not bids.

## Credentials

- `PLATFORM_MCP_FREELANCER_ACCESS_TOKEN` — Freelancer OAuth access token sent as the freelancer-oauth-v1 header: a Personal Access Token from https://accounts.freelancer.com/settings/develop ('valid for thirty days') or a token from your registered OAuth app (scopes basic, fln:project_manage, fln:messaging, fln:user_information as needed).
- `PLATFORM_MCP_FREELANCER_BIDDER_ID` — Your Freelancer user id (GET /users/0.1/self/ → result.id); required by POST /projects/0.1/bids/ as bidder_id.
- `PLATFORM_MCP_FREELANCER_MILESTONE_PERCENTAGE` — Initial milestone percentage (20–100) required by POST /projects/0.1/bids/ ('Please fill in the milestone percentage (20 - 100)').

## Run

    uvx platform-mcp-hub serve deals/freelancer          # Python
    npx -y platform-mcp-hub serve deals/freelancer       # TypeScript
    claude mcp add freelancer -- uvx platform-mcp-hub serve deals/freelancer

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/freelancer-deals-mcp`. Python and TypeScript serve identical tools.

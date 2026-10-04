# Belancer MCP server

Category: **deals** · Docs: https://belancer.com/api/docs · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/belancer_com.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /auth/me` (https://belancer.com/api/docs)
- `search_postings` — `GET /projects/search` (https://belancer.com/api/docs)
- `get_posting` — `GET /projects/{id}` (https://belancer.com/api/docs)
- ~~`submit_bid`~~ not offered: POST /projects/{project_id}/bids exists in the OpenAPI, but bid submission stays closed until Belancer's written permission for third-party bidding is recorded (terms unreadable; no developer programme).
- ~~`withdraw_bid`~~ not offered: Bid writes stay closed (see submit_bid).
- ~~`bid_status`~~ not offered: Bid endpoints are kept closed together with submit_bid until Belancer permits third-party use.
- ~~`list_messages`~~ not offered: Project messages are addressed by two ids (GET /messages/project/{project_id}/{receiver_id}); the vocabulary's thread_id cannot carry both.
- ~~`send_message`~~ not offered: Sending needs project_id and receiver_id (POST /messages/project/{project_id}/{receiver_id}); the vocabulary's thread_id cannot carry both.
- ~~`credits`~~ not offered: Bid credits (bid_credit_cost per project) have no balance endpoint in the OpenAPI.

## Credentials

- `PLATFORM_MCP_BELANCER_COM_USERNAME` — E-mail address of your Belancer account (POST /auth/login validates username as an e-mail).
- `PLATFORM_MCP_BELANCER_COM_PASSWORD` — Password of the same Belancer account.

## Run

    uvx platform-mcp-hub serve belancer_com          # Python
    npx -y platform-mcp-hub serve belancer_com       # TypeScript
    claude mcp add belancer_com -- uvx platform-mcp-hub serve belancer_com

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/belancer_com-mcp`. Python and TypeScript serve identical tools.

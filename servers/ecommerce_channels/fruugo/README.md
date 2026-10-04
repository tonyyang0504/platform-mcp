# Fruugo MCP server

Category: **ecommerce_channels** · Docs: https://fruugo.atlassian.net/wiki/spaces/RR/pages/66158670/Order+API · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/fruugo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /orders/download/v2` (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66158675/Requests+Calls)
- `list_orders` — `GET /orders/download/v2` (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66158675/Requests+Calls)
- `mark_shipped` — `POST /orders/ship` (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66158675/Requests+Calls)
- `set_inventory` — `POST /stockstatus-api` (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66682960/Stock+Inventory+Update)
- `end_listing` — `POST /stockstatus-api` (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66682960/Stock+Inventory+Update)
- ~~`create_listing`~~ not offered: Products are only created from the retailer's CSV/XML product feed that Fruugo fetches from a URL (https://fruugo.atlassian.net/wiki/spaces/RR/pages/67608002/Fruugo+Feed); there is no product-creation API call.
- ~~`update_listing`~~ not offered: "The API doesn't allow the update of other product information such as title or price - these must be controlled by the product feed" (https://fruugo.atlassian.net/wiki/spaces/RR/pages/66682954/Stock+Status+API); stock is set_inventory.

## Credentials

- `PLATFORM_MCP_FRUUGO_USERNAME` — Fruugo Retailer Portal login (the Order and Stock Status APIs use the portal credentials with HTTP Basic).
- `PLATFORM_MCP_FRUUGO_PASSWORD` — Fruugo Retailer Portal password.

## Run

    uvx platform-mcp-hub serve fruugo          # Python
    npx -y platform-mcp-hub serve fruugo       # TypeScript
    claude mcp add fruugo -- uvx platform-mcp-hub serve fruugo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/fruugo-mcp`. Python and TypeScript serve identical tools.

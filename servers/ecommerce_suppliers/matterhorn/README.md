# Matterhorn MCP server

Category: **ecommerce_suppliers** · Docs: https://matterhorn-wholesale.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/matterhorn.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /DICTIONARIES/CATEGORIES` (https://matterhorn-wholesale.com/?str=api-help)
- `list_products` — `GET /ITEMS/` (https://matterhorn-wholesale.com/?str=api-help)
- `get_product` — `GET /ITEMS/{id}` (https://matterhorn-wholesale.com/?str=api-help)
- `create_order` — `PUT /ACCOUNT/ORDERS/` (https://matterhorn-wholesale.com/?str=api-help)
- `get_order` — `GET /ACCOUNT/ORDERS/{id}` (https://matterhorn-wholesale.com/?str=api-help)
- ~~`quote_shipping`~~ not offered: Delivery methods per country come from GET /B2BAPI/DICTIONARIES/DELIVERY/{country}, but the api-help page does not document its response fields (the SwaggerHub reference it points to is not linked readably), so the options cannot be mapped reliably.
- ~~`track`~~ not offered: No tracking-events endpoint; the order carries shipping_service, shipping_number and tracking_url once shipped (see get_order).

## Credentials

- `PLATFORM_MCP_MATTERHORN_API_KEY` — Matterhorn REST API key generated in the customer panel (free for registered wholesale customers), sent as the raw Authorization header value.
- `PLATFORM_MCP_MATTERHORN_CURRENCY` — Order currency for create_order (e.g. EUR, USD, GBP); left out of the body when unset.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve matterhorn   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve matterhorn
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve matterhorn   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/matterhorn-mcp`. Python and TypeScript serve identical tools.

# OTTO Market MCP server

Category: **ecommerce_channels** · Docs: https://api.otto.market/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/otto.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/availability/quantities` (https://api.otto.market/docs/functional-interfaces/availability)
- `update_listing` — `POST /v5/products/prices` (https://api.otto.market/docs/functional-interfaces/products)
- `set_inventory` — `POST /v1/availability/quantities` (https://api.otto.market/docs/functional-interfaces/availability)
- `end_listing` — `POST /v5/products/active-status` (https://api.otto.market/docs/functional-interfaces/products)
- `list_orders` — `GET /v4/orders` (https://api.otto.market/docs/functional-interfaces/orders)
- ~~`create_listing`~~ not offered: POST /v5/products takes full product variations (productReference, category, brand, attributes, media, delivery, pricing) and requires a shipping profile assignment before the SKU becomes orderable; the vocabulary lacks category, brand and attributes.
- ~~`mark_shipped`~~ not offered: POST /v1/shipments requires shipDate, shipFromAddress and, per position item, positionItemId + salesOrderId + a RETURN tracking key; position items and return labels are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_OTTO_CLIENT_ID` — Client ID of a self-app created in OTTO Partner Connect > API access with the Products, Availability, Orders and Shipments interfaces enabled (https://api.otto.market/docs/sellers-integration).
- `PLATFORM_MCP_OTTO_CLIENT_SECRET` — The app's client secret (shown once in Partner Connect). Tokens are minted with the client credentials and the scopes 'products availability orders shipments'.
- `PLATFORM_MCP_OTTO_CURRENCY` — Price currency for update_listing, EUR for otto.de.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve otto   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve otto
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve otto   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/otto-mcp`. Python and TypeScript serve identical tools.

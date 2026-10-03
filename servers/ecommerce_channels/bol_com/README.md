# bol.com MCP server

Category: **ecommerce_channels** · Docs: https://api.bol.com/retailer/public/Retailer-API/v10/releasenotes.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/bol_com.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /retailer/orders` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/get-orders)
- `update_listing` — `PUT /retailer/offers/{listing_id}/price` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/update-offer-price)
- `set_inventory` — `PUT /retailer/offers/{listing_id}/stock` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/update-offer-stock)
- `end_listing` — `DELETE /retailer/offers/{listing_id}` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/delete-offer)
- `list_orders` — `GET /retailer/orders` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/get-orders)
- `mark_shipped` — `POST /retailer/shipments` (https://api.bol.com/retailer/public/redoc/v10/retailer.html#operation/create-shipment)
- ~~`create_listing`~~ not offered: POST /retailer/offers needs the product EAN, condition and fulfilment method/delivery code plus pricing and stock; the vocabulary has no EAN or condition (sku is not bol's product key).

## Credentials

- `PLATFORM_MCP_BOL_COM_CLIENT_ID` — Client ID of Retailer API credentials created in the bol Seller Dashboard (Settings > API settings); exchanged at POST https://login.bol.com/token (grant_type=client_credentials, HTTP Basic) for a short-lived (~5 minute) JWT.
- `PLATFORM_MCP_BOL_COM_CLIENT_SECRET` — The matching client secret. The token is cached until expiry (bol blocks clients that request a token for every call).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bol_com   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bol_com
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bol_com   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bol_com-mcp`. Python and TypeScript serve identical tools.

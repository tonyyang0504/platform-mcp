# Vinted Pro MCP server

Category: **ecommerce_channels** · Docs: https://pro-docs.svc.vinted.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/vinted_pro.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v1/items` (https://pro-docs.svc.vinted.com/#getitems)
- `end_listing` — `DELETE /api/v1/items` (https://pro-docs.svc.vinted.com/#deleteitems)
- `list_orders` — `GET /api/v1/orders` (https://pro-docs.svc.vinted.com/#getorders)
- ~~`create_listing`~~ not offered: CreateItems requires brand, catalog_id, package_size_id, currency, photo_urls and the category's item attributes resolved from GetOntologies; the vocabulary has no catalogue, brand or package size.
- ~~`update_listing`~~ not offered: UpdateItems replaces the whole item: brand, catalog_id, currency, description, package_size_id, photo_urls, price, title and is_draft are all required for every update, so a price-only change is not possible.
- ~~`set_inventory`~~ not offered: Vinted items are single second-hand listings without a stock quantity; there is no stock endpoint.
- ~~`mark_shipped`~~ not offered: Shipping uses the Vinted-issued label (GetOrderShipmentLabel) and the carrier's own tracking; there is no call to submit a carrier and tracking number.

## Credentials

- `PLATFORM_MCP_VINTED_PRO_ACCESS_KEY` — Access key: the part BEFORE the comma of the access token generated in the Vinted Pro Integrations Portal (tokens are shown only once; production and dev mode have separate tokens); sent as X-Vpi-Access-Key.
- `PLATFORM_MCP_VINTED_PRO_SIGNING_KEY` — Signing key: the part AFTER the comma of the same access token. Signs every request (hex HMAC-SHA256 over '<unix seconds>.<METHOD>.<path+query>.<access key>.<body>', sent as X-Vpi-Hmac-Sha256: t=<ts>,v1=<hash>); never sent on the wire.
- `PLATFORM_MCP_VINTED_PRO_API_HOST` — pro.svc.vinted.com (production) or pro-public-sandbox.svc.vinted.com (dev mode).

## Run

    uvx platform-mcp-hub serve vinted_pro          # Python
    npx -y platform-mcp-hub serve vinted_pro       # TypeScript
    claude mcp add vinted_pro -- uvx platform-mcp-hub serve vinted_pro

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/vinted_pro-mcp`. Python and TypeScript serve identical tools.

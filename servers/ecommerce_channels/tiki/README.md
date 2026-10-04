# Tiki MCP server

Category: **ecommerce_channels** · Docs: https://open.tiki.vn/docs/docs/current/getting-started/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/tiki.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/sellers/me` (https://open.tiki.vn/docs/docs/current/api-references/seller-api/)
- `update_listing` — `PUT /v2/products/updateSku` (https://open.tiki.vn/docs/docs/current/guides/products/update-product-information/)
- `set_inventory` — `PUT /v2/products/updateSku` (https://open.tiki.vn/docs/docs/current/guides/products/update-product-information/)
- `end_listing` — `PUT /v2.1/products/updateSkus` (https://open.tiki.vn/docs/docs/current/guides/products/update-product-information/)
- `list_orders` — `GET /v2/orders` (https://open.tiki.vn/docs/docs/current/api-references/order-api-v2/)
- ~~`create_listing`~~ not offered: New products are product REQUESTS (POST /integration/v2.1/requests) with category, attributes, images and option data that Tiki reviews; the vocabulary has no category or attributes.
- ~~`mark_shipped`~~ not offered: Tiki's logistics partners carry most orders ('For other operation models, you don't need to update delivery status… already handled by Tiki'); seller-delivery orders only report a delivery OUTCOME (POST /integration/v2/orders/{code}/seller-delivery/update-delivery {status: successful_delivery|failed…}) and there is no call that submits a carrier and tracking number.

## Credentials

- `PLATFORM_MCP_TIKI_CLIENT_ID` — App id of an IN-HOUSE application registered on the Tiki Open Platform and connected to your seller store (in-house apps receive the seller's permissions via the client-credentials flow).
- `PLATFORM_MCP_TIKI_CLIENT_SECRET` — App secret of the same application; sent with the id as HTTP Basic (client_secret_basic) to https://api.tiki.vn/sc/oauth2/token. Apps configured for client_secret_post are not supported by this adapter.
- `PLATFORM_MCP_TIKI_WAREHOUSE_ID` — Seller warehouse id (GET /integration/v2/sellers/me/warehouses) whose available quantity set_inventory writes.

## Run

    uvx platform-mcp-hub serve tiki          # Python
    npx -y platform-mcp-hub serve tiki       # TypeScript
    claude mcp add tiki -- uvx platform-mcp-hub serve tiki

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tiki-mcp`. Python and TypeScript serve identical tools.

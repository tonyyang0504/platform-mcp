# eMAG Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://marketplace.emag.ro/infocenter/emag-academy/how-to-add-a-product/product-import-through-api-or-feeds/api-documentation/?lang=en · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/emag.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /vat/read` (https://marketplace-api.emag.ro/api-doc#operation/readVAT)
- `update_listing` — `POST /offer/save` (https://marketplace-api.emag.ro/api-doc#operation/saveOffer)
- `set_inventory` — `PATCH /offer_stock/{listing_id}` (https://marketplace-api.emag.ro/api-doc#operation/updateOfferStock)
- `end_listing` — `POST /offer/save` (https://marketplace-api.emag.ro/api-doc#operation/saveOffer)
- `list_orders` — `POST /order/read` (https://marketplace-api.emag.ro/api-doc#operation/readOrders)
- ~~`create_listing`~~ not offered: New offers go through POST /product_offer/save, which needs category_id, part_number, brand, characteristics, vat_id, handling_time and stock per warehouse (or an attach by EAN/part_number_key); the vocabulary has no category, brand or VAT inputs.
- ~~`mark_shipped`~~ not offered: There is no tracking-number call: shipping is done by issuing an AWB with an eMAG courier account (POST /awb/save, sender/receiver/parcels), and finalising an order (status 4) goes through POST /order/save, which requires ALL order fields initially read ('When updating an order, send ALL the fields initially read').

## Credentials

- `PLATFORM_MCP_EMAG_USERNAME` — Username of the API user created in your eMAG Marketplace seller account (the user must be granted API rights, and eMAG only accepts calls from the IPs you whitelisted with them); sent as HTTP Basic.
- `PLATFORM_MCP_EMAG_PASSWORD` — Password of that API user; sent as HTTP Basic.
- `PLATFORM_MCP_EMAG_API_HOST` — API host of your platform: marketplace-api.emag.ro (eMAG RO), marketplace-api.emag.bg (BG), marketplace-api.emag.hu (HU), marketplace-ro-api.fashiondays.com or marketplace-bg-api.fashiondays.com (Fashion Days); calls go to https://<api_host>/api-3/...

## Run

    uvx platform-mcp-hub serve emag          # Python
    npx -y platform-mcp-hub serve emag       # TypeScript
    claude mcp add emag -- uvx platform-mcp-hub serve emag

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/emag-mcp`. Python and TypeScript serve identical tools.

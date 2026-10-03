# Newegg Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://developer.newegg.com/newegg_marketplace_api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/newegg.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sellermgmt/seller/accountstatus` (https://developer.newegg.com/newegg_marketplace_api/seller_management/seller_status_check/)
- `update_listing` — `POST /contentmgmt/item/international/price` (https://developer.newegg.com/newegg_marketplace_api/item_management/update_item_price/)
- `end_listing` — `POST /contentmgmt/item/international/price` (https://developer.newegg.com/newegg_marketplace_api/item_management/update_item_price/)
- `set_inventory` — `POST /contentmgmt/item/international/inventory` (https://developer.newegg.com/newegg_marketplace_api/item_management/update_item_inventory/)
- `list_orders` — `PUT /ordermgmt/order/orderinfo` (https://developer.newegg.com/newegg_marketplace_api/order_management/get_order_information/)
- ~~`create_listing`~~ not offered: Item creation goes through datafeeds (Item Creation feed with subcategory properties, manufacturer, UPC/MPN) — an asynchronous file submission, not a single call with the vocabulary's fields.
- ~~`mark_shipped`~~ not offered: Ship Order (PUT /ordermgmt/orderstatus/orders/{ordernumber}) requires per package ShipCarrier, ShipService and an ItemList of SellerPartNumber + ShippedQty; items and ship service are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_NEWEGG_API_KEY` — Newegg Marketplace API key assigned by the Newegg integration team (or your third-party developer key); sent verbatim as the Authorization header.
- `PLATFORM_MCP_NEWEGG_SECRET_KEY` — The seller's Secret Key (assigned to you, or to your third-party developer on the seller's authorization); sent as the SecretKey header.
- `PLATFORM_MCP_NEWEGG_SELLER_ID` — Your Newegg seller ID (e.g. A006); sent as ?sellerid= on every call.
- `PLATFORM_MCP_NEWEGG_COUNTRY_CODE` — ISO 3-letter ship-to country your prices target, e.g. USA; used in PriceList.Price[].CountryCode by update_listing/end_listing.
- `PLATFORM_MCP_NEWEGG_CURRENCY` — Currency matching country_code, e.g. USD for USA (wrong combinations are rejected).
- `PLATFORM_MCP_NEWEGG_WAREHOUSE_LOCATION` — ISO 3-letter country of the warehouse whose stock set_inventory writes, e.g. USA.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve newegg   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve newegg
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve newegg   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/newegg-mcp`. Python and TypeScript serve identical tools.

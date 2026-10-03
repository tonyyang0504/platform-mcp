# Takealot Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://seller-api.takealot.com/api-docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/takealot.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/offers/count` (https://seller-api.takealot.com/api-docs/#/Offers%20(v2)/get_offers_count_v2)
- `update_listing` — `PATCH /v2/offers/offer/{listing_id}` (https://seller-api.takealot.com/api-docs/#/Offers%20(v2)/update_offer_by_identifier_v2)
- `set_inventory` — `PATCH /v2/offers/offer/{identifier}` (https://seller-api.takealot.com/api-docs/#/Offers%20(v2)/update_offer_by_identifier_v2)
- `end_listing` — `PATCH /v2/offers/offer/{listing_id}` (https://seller-api.takealot.com/api-docs/#/Offers%20(v2)/update_offer_by_identifier_v2)
- ~~`create_listing`~~ not offered: POST /v2/offers/offer/{barcode} creates an offer on an existing Takealot catalogue product identified by its barcode, with whole-rand selling_price/rrp and leadtime data; the vocabulary has no barcode.
- ~~`list_orders`~~ not offered: GET /v1/sales/orders requires both start_date AND end_date (swagger get_sales_orders); the vocabulary has only `since` and the runtime cannot derive an end date.
- ~~`mark_shipped`~~ not offered: Takealot fulfils customer orders from its distribution centres (sellers ship leadtime stock to Takealot via purchase orders); the Seller API has no customer-shipment or tracking call.

## Credentials

- `PLATFORM_MCP_TAKEALOT_AUTHORIZATION` — The complete Authorization header value for your Seller API key exactly as the Takealot Seller Portal shows it (Seller Portal > API, https://seller.takealot.com/api/seller-api — generate the key there; the public reference only says to 'attach an Authorization header' and defers the format to that page).
- `PLATFORM_MCP_TAKEALOT_MERCHANT_WAREHOUSE_ID` — Your leadtime merchant_warehouse_id (listed at https://seller.takealot.com/api/seller-api/offers); required by set_inventory.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve takealot   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve takealot
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve takealot   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/takealot-mcp`. Python and TypeScript serve identical tools.

# Gooten MCP server

Category: **ecommerce_suppliers** · Docs: https://www.gooten.com/api-documentation/getting-started/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/gooten.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v/5/source/api/countries/` (https://www.gooten.com/api-documentation/getting-supported-shipping-to-countries/)
- `list_products` — `GET /api/v/5/source/api/prpproducts/` (https://www.gooten.com/api-documentation/print-ready-products/)
- `create_order` — `POST /api/v/5/source/api/orders/` (https://www.gooten.com/api-documentation/submitting-an-order/)
- `get_order` — `GET /api/v/5/source/api/orders/` (https://www.gooten.com/api-documentation/get-order-by-id/)
- `track` — `GET /api/v/5/source/api/orders/` (https://www.gooten.com/api-documentation/get-order-by-id/)
- ~~`get_product`~~ not offered: Product variants (GET productvariants/?productId=&countryCode=) return ProductVariants[{Sku, Options, PriceInfo}] without a product title or id record, and the catalogue itself is a static CDN file (productdatav3/catalog.json), so there is no single-product read to map.
- ~~`quote_shipping`~~ not offered: GET shippriceestimate/?productId=&countryCode=&currencyCode= answers one {MinPrice, MaxPrice, EstShipDays, CanShipExpedited} estimate rather than a list of shipping options, and currencyCode is required; POST shippingprices needs a full cart (ShipToCountry, Items[{SKU, Quantity}]).

## Credentials

- `PLATFORM_MCP_GOOTEN_RECIPE_ID` — Gooten RecipeID (public key, Admin Panel > Settings > API), sent as the `recipeid` query parameter on every call.
- `PLATFORM_MCP_GOOTEN_PARTNER_BILLING_KEY` — Gooten PartnerBillingKey (private key from the same API settings page), sent inside create_order's Payment object so Gooten bills your account; required only for create_order.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve gooten   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve gooten
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve gooten   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gooten-mcp`. Python and TypeScript serve identical tools.

# Squarespace Commerce MCP server

Category: **ecommerce_channels** · Docs: https://developers.squarespace.com/commerce-apis/overview · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/squarespace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/commerce/products` (https://developers.squarespace.com/commerce-apis/products-overview)
- `end_listing` — `POST /v2/commerce/products/{listing_id}` (https://developers.squarespace.com/commerce-apis/update-product)
- `list_orders` — `GET /1.0/commerce/orders` (https://developers.squarespace.com/commerce-apis/retrieve-all-orders)
- ~~`create_listing`~~ not offered: POST /v2/commerce/products requires `storePageId` and a `variants[{sku, pricing{basePrice{value, currency}}, stock{quantity}}]` array of objects — the price lives inside the array, which the flat/dotted body cannot express.
- ~~`update_listing`~~ not offered: POST /v2/commerce/products/{productId} takes every field as a {present: true, value} change object (ChangeString / ChangeUpdateProductPricing); `present` would have to be sent only for the arguments actually given, but the body form sends literals unconditionally, so a partial update (e.g. description only) would also send name/pricing wrappers without a value, whose effect is undocumented.
- ~~`set_inventory`~~ not offered: POST /1.0/commerce/inventory/adjustments takes setFiniteOperations[{variantId, quantity}] (an array of objects, not expressible) and answers 204 No Content.
- ~~`mark_shipped`~~ not offered: POST /1.0/commerce/orders/{id}/fulfillments takes shouldSendNotification (boolean) and shipments[{carrierName, trackingNumber, trackingUrl, shipDate}] (an array of objects) and answers 204 No Content — not expressible in the flat/dotted body.
- ~~`listing_metrics`~~ not offered: The Commerce APIs expose Transactions (financial records) but no per-product views or conversion metrics.

## Credentials

- `PLATFORM_MCP_SQUARESPACE_API_KEY` — Developer API key (Commerce Advanced plan: Settings > Advanced > Developer API Keys; Orders read, Products read) sent as `Authorization: Bearer`; the docs also require a descriptive User-Agent, which the runtime sends.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve squarespace   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve squarespace
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve squarespace   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/squarespace-mcp`. Python and TypeScript serve identical tools.

# orosy (wholesale marketplace) + orosy Buyer API MCP server

Category: **ecommerce_suppliers** · Docs: https://wholesale-portal.orosy.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/orosy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/me` (https://wholesale-api.orosy.com/docs)
- `list_products` — `GET /v1/products` (https://wholesale-api.orosy.com/docs)
- `get_product` — `GET /v1/products/{product_id}` (https://wholesale-api.orosy.com/docs)
- `quote_shipping` — `GET /v1/cross-border/eligibility` (https://wholesale-api.orosy.com/docs)
- `get_order` — `GET /v1/orders/{order_id}` (https://wholesale-api.orosy.com/docs)
- `track` — `GET /v1/orders/{order_id}` (https://wholesale-api.orosy.com/docs)
- ~~`create_order`~~ not offered: POST /v1/orders 'カート全件で注文を作成します' (creates the order from the whole server-side cart): items must first be added one variation at a time with PUT /v1/cart/items (and the destination set with PUT /v1/cart/ship-to), and the AI flow is meant to stop at the total for a human to confirm. A single call cannot build the cart from the vocabulary's items array; orosy's official MCP endpoint https://wholesale-api.orosy.com/mcp covers cart and ordering.

## Credentials

- `PLATFORM_MCP_OROSY_API_KEY` — orosy Buyer API key (orosy_live_…) issued in the portal after the business review (事業者確認), sent as `Authorization: Bearer` ('OAuth 不要'). Before approval the account works in test mode on demo data.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve orosy   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve orosy
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve orosy   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/orosy-mcp`. Python and TypeScript serve identical tools.

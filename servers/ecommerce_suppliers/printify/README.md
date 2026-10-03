# Printify MCP server

Category: **ecommerce_suppliers** · Docs: https://developers.printify.com/ · Verified: None

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/printify.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /shops.json` (https://developers.printify.com/#shops)
- `list_products` — `GET /catalog/blueprints.json` (https://developers.printify.com/#catalog)
- `get_product` — `GET /catalog/blueprints/{id}.json` (https://developers.printify.com/#catalog)
- `create_order` — `POST /shops/{shop_id}/orders.json` (https://developers.printify.com/#orders)
- `get_order` — `GET /shops/{shop_id}/orders/{id}.json` (https://developers.printify.com/#orders)
- ~~`quote_shipping`~~ not offered: POST /v1/shops/{shop_id}/orders/shipping.json takes nested line_items[{product_id, variant_id, quantity}] + address_to{country, region, ...}; the vocabulary's product_id/country/quantity cannot be shaped into that body by the runtime's flat body form.
- ~~`track`~~ not offered: No tracking-events endpoint; shipments[{carrier, number, url, delivered_at}] are part of the order record (see get_order).

## Credentials

- `PLATFORM_MCP_PRINTIFY_TOKEN` — Printify personal access token (My profile > Connections) sent as `Authorization: Bearer`.
- `PLATFORM_MCP_PRINTIFY_SHOP_ID` — Printify shop id (from GET /v1/shops.json); required by get_order and create_order, which are per shop.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve printify   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve printify
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve printify   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/printify-mcp`. Python and TypeScript serve identical tools.

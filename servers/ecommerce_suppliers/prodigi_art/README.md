# Prodigi — art prints / wall art (cross-ref prodigi in the POD table) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.prodigi.com/print-api/docs/reference/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/prodigi_art.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /Orders` (https://www.prodigi.com/print-api/docs/reference/#orders)
- `get_product` — `GET /products/{id}` (https://www.prodigi.com/print-api/docs/reference/#products)
- `create_order` — `POST /Orders` (https://www.prodigi.com/print-api/docs/reference/#orders)
- `get_order` — `GET /Orders/{id}` (https://www.prodigi.com/print-api/docs/reference/#orders)
- `quote_shipping` — `POST /quotes` (https://www.prodigi.com/print-api/docs/reference/#create-quote)
- ~~`list_products`~~ not offered: No catalogue browse endpoint: products are SKUs chosen in the Prodigi dashboard; GET /v4.0/products/{sku} only reads one.
- ~~`track`~~ not offered: No tracking-events endpoint; shipments[{carrier{name, service}, tracking{number, url}}] are part of the order record (see get_order).

## Credentials

- `PLATFORM_MCP_PRODIGI_ART_API_KEY` — Prodigi API key for the LIVE environment (dashboard), sent as `X-API-Key`. A Sandbox key needs PLATFORM_MCP_PRODIGI_ART_ENV=sandbox (https://api.sandbox.prodigi.com/v4.0).
- `PLATFORM_MCP_PRODIGI_ART_ENV` — Vendor environment (default production): sandbox = https://api.sandbox.prodigi.com/v4.0. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_PRODIGI_ART_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve prodigi_art          # Python
    npx -y platform-mcp-hub serve prodigi_art       # TypeScript
    claude mcp add prodigi_art -- uvx platform-mcp-hub serve prodigi_art

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/prodigi_art-mcp`. Python and TypeScript serve identical tools.

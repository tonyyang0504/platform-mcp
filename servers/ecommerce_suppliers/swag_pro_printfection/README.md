# Swag Pro (formerly Printfection) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.printfection.com/developers/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/swag_pro_printfection.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /campaigns` (https://printfection.github.io/API-Documentation/#campaigns)
- `list_products` — `GET /items` (https://printfection.github.io/API-Documentation/#items)
- `get_product` — `GET /items/{id}` (https://printfection.github.io/API-Documentation/#items)
- `create_order` — `POST /orders` (https://printfection.github.io/API-Documentation/#orders)
- `get_order` — `GET /orders/{id}` (https://printfection.github.io/API-Documentation/#orders)
- `track` — `GET /orders/{order_id}` (https://printfection.github.io/API-Documentation/#orders)
- ~~`quote_shipping`~~ not offered: No shipping-quote endpoint; the API covers items, orders, lineitems and campaigns only, and shipping cost appears in an order's manifest after processing.

## Credentials

- `PLATFORM_MCP_SWAG_PRO_PRINTFECTION_API_KEY` — Swag Pro (Printfection) API key from https://app.printfection.com/account/api_keys.php, sent as the HTTP Basic username with an empty password.
- `PLATFORM_MCP_SWAG_PRO_PRINTFECTION_CAMPAIGN_ID` — Numeric id of the Collection campaign create_order places orders in (GET /campaigns, not mapped). Only Giveaway and Collection campaigns are supported by the API.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve swag_pro_printfection   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve swag_pro_printfection
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve swag_pro_printfection   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/swag_pro_printfection-mcp`. Python and TypeScript serve identical tools.

# vidaXL B2B dropshipping MCP server

Category: **ecommerce_suppliers** · Docs: https://b2b.vidaxl.com/pages/8-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/vidaxl_dropship.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api_customer/products` (https://b2b.vidaxl.com/pages/8-api)
- `list_products` — `GET /api_customer/products` (https://b2b.vidaxl.com/pages/8-api)
- `get_product` — `GET /api_customer/products` (https://b2b.vidaxl.com/pages/8-api)
- `create_order` — `POST /api_customer/orders` (https://b2b.vidaxl.com/pages/8-api)
- `get_order` — `GET /api_customer/orders` (https://b2b.vidaxl.com/pages/8-api)
- ~~`quote_shipping`~~ not offered: The order API has no shipping-quote endpoint (only create order, get orders, invoices and products are documented).
- ~~`track`~~ not offered: No tracking-events endpoint; shipping_tracking and shipping_tracking_url are part of the order record (see get_order).

## Credentials

- `PLATFORM_MCP_VIDAXL_DROPSHIP_EMAIL` — The vidaXL B2B customer e-mail (HTTP Basic username).
- `PLATFORM_MCP_VIDAXL_DROPSHIP_API_TOKEN` — API token shown under MY ACCOUNT on b2b.vidaxl.com (HTTP Basic password). Sandbox tokens belong to https://sandbox.b2b.vidaxl.com, which this server does not switch to.

## Run

    uvx platform-mcp-hub serve vidaxl_dropship          # Python
    npx -y platform-mcp-hub serve vidaxl_dropship       # TypeScript
    claude mcp add vidaxl_dropship -- uvx platform-mcp-hub serve vidaxl_dropship

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/vidaxl_dropship-mcp`. Python and TypeScript serve identical tools.

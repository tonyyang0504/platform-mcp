# CustomCat MCP server

Category: **ecommerce_suppliers** · Docs: https://help.customcat.com/getting-started-with-customcat-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/customcat.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /catalogcategory` (https://customcat-beta.mylocker.net/api/v1/)
- `list_products` — `GET /product` (https://customcat-beta.mylocker.net/api/v1/)
- `create_order` — `POST /order/{order_id}` (https://customcat-beta.mylocker.net/api/v1/)
- `get_order` — `GET /order/status/{order_id}` (https://customcat-beta.mylocker.net/api/v1/)
- `track` — `GET /order/status/{order_id}` (https://customcat-beta.mylocker.net/api/v1/)
- ~~`get_product`~~ not offered: GET /product/{product_id} is listed but its response is not documented (only the /product list response is), so no field mapping can be grounded in the docs.
- ~~`quote_shipping`~~ not offered: GET /shipping lists methods for a country and POST /shipping/{shipping_id} prices items[{catalog_sku, quantity}] for one method, but neither response shape is documented, so no options list can be mapped.

## Credentials

- `PLATFORM_MCP_CUSTOMCAT_API_KEY` — CustomCat API key (generated per 'API Custom Integrations' store; Settings in the app shows a read-only and a read-write key — create_order needs the read-write one), sent as the `api_key` parameter.
- `PLATFORM_MCP_CUSTOMCAT_SANDBOX` — Set to 1 to send `sandbox: 1` with create_order and get_order (CustomCat's sandbox flag); left out when unset, so orders are real and charged.

## Run

    uvx platform-mcp-hub serve customcat          # Python
    npx -y platform-mcp-hub serve customcat       # TypeScript
    claude mcp add customcat -- uvx platform-mcp-hub serve customcat

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/customcat-mcp`. Python and TypeScript serve identical tools.

# WooCommerce MCP server

Category: **ecommerce_channels** · Docs: https://developer.woocommerce.com/docs/apis/rest-api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/woocommerce.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://{store_host}/wp-json/wc/v3/system_status` (https://woocommerce.github.io/woocommerce-rest-api-docs/#system-status)
- `create_listing` — `POST https://{store_host}/wp-json/wc/v3/products` (https://woocommerce.github.io/woocommerce-rest-api-docs/#create-a-product)
- `update_listing` — `PUT https://{store_host}/wp-json/wc/v3/products/{listing_id}` (https://woocommerce.github.io/woocommerce-rest-api-docs/#update-a-product)
- `end_listing` — `PUT https://{store_host}/wp-json/wc/v3/products/{listing_id}` (https://woocommerce.github.io/woocommerce-rest-api-docs/#update-a-product)
- `set_inventory` — `PUT https://{store_host}/wp-json/wc/v3/products/{listing_id}` (https://woocommerce.github.io/woocommerce-rest-api-docs/#update-a-product)
- `list_orders` — `GET https://{store_host}/wp-json/wc/v3/orders` (https://woocommerce.github.io/woocommerce-rest-api-docs/#list-all-orders)
- `mark_shipped` — `PUT https://{store_host}/wp-json/wc/v3/orders/{order_id}` (https://woocommerce.github.io/woocommerce-rest-api-docs/#update-an-order)
- ~~`listing_metrics`~~ not offered: No per-product analytics endpoint: GET /wp-json/wc/v3/reports/* are store-wide sales / top-sellers reports, not views or conversions for one listing.

## Credentials

- `PLATFORM_MCP_WOOCOMMERCE_CONSUMER_KEY` — WooCommerce REST API consumer key (WooCommerce > Settings > Advanced > REST API > Add key, Read/Write) sent as the HTTP Basic username over HTTPS.
- `PLATFORM_MCP_WOOCOMMERCE_CONSUMER_SECRET` — The consumer secret shown once when the key is created; sent as the HTTP Basic password.
- `PLATFORM_MCP_WOOCOMMERCE_STORE_HOST` — Host (and any path prefix) of the merchant's WooCommerce store without scheme, e.g. shop.example.com or example.com/shop; every call goes to https://<store_host>/wp-json/wc/v3/... (HTTPS only: Basic auth with the consumer key/secret is documented for HTTPS; plain-HTTP stores need OAuth 1.0a, not supported).

## Run

    uvx platform-mcp-hub serve woocommerce          # Python
    npx -y platform-mcp-hub serve woocommerce       # TypeScript
    claude mcp add woocommerce -- uvx platform-mcp-hub serve woocommerce

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/woocommerce-mcp`. Python and TypeScript serve identical tools.

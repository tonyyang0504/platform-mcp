# Shopify MCP server

Category: **builder_tools** · Docs: https://shopify.dev/docs/api/admin-rest · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/shopify.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /shop.json` (https://shopify.dev/docs/api/admin-rest/latest/resources/shop)
- `list_items` — `POST /graphql.json` (https://shopify.dev/docs/api/admin-graphql/latest/queries/products)
- `get_item` — `GET /products/{item_id}.json` (https://shopify.dev/docs/api/admin-rest/latest/resources/product#get-products-product-id)
- `create_item` — `POST /products.json` (https://shopify.dev/docs/api/admin-rest/latest/resources/product#post-products)
- `update_item` — `PUT /products/{item_id}.json` (https://shopify.dev/docs/api/admin-rest/latest/resources/product#put-products-product-id)
- `delete_item` — `DELETE /products/{item_id}.json` (https://shopify.dev/docs/api/admin-rest/latest/resources/product#delete-products-product-id)
- ~~`generate_image`~~ not offered: The Admin API has no image generation endpoint.
- ~~`generate_video`~~ not offered: The Admin API has no video generation endpoint.
- ~~`get_job`~~ not offered: No generation jobs in the Admin API.

## Credentials

- `PLATFORM_MCP_SHOPIFY_ACCESS_TOKEN` — Admin API access token of a custom app installed on the store (Settings > Apps and sales channels > Develop apps), with read_products/write_products scopes; sent as X-Shopify-Access-Token.
- `PLATFORM_MCP_SHOPIFY_SHOP` — The store's myshopify subdomain (the part before .myshopify.com).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve shopify   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve shopify
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve shopify   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shopify-mcp`. Python and TypeScript serve identical tools.

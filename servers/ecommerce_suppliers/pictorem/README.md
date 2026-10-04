# Pictorem PRO (white-label dropship + API Print on Demand) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.pictorem.com/apiprintondemand · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/pictorem.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /getorderlist/` (https://www.pictorem.com/artflow/0.1/docs/)
- `list_products` — `POST /getartworklist/` (https://www.pictorem.com/artflow/0.1/docs/)
- `create_order` — `POST /sendorder/` (https://www.pictorem.com/artflow/0.1/docs/)
- `get_order` — `POST /getorderstatus/` (https://www.pictorem.com/artflow/0.1/docs/)
- `track` — `POST /getorderstatus/` (https://www.pictorem.com/artflow/0.1/docs/)
- ~~`get_product`~~ not offered: There is no single-product endpoint: products are preordercodes validated with validatepreorder and priced with getprice (https://www.pictorem.com/artflow/0.1/docs/), and artworks are only listed in pages by getartworklist.
- ~~`quote_shipping`~~ not offered: getshippingquote requires 'deliveryInfo[city] text *', 'deliveryInfo[province] text *' and 'deliveryInfo[cp] text *' plus the product code (https://www.pictorem.com/artflow/0.1/docs/); the vocabulary's quote_shipping has only product_id, country and quantity.

## Credentials

- `PLATFORM_MCP_PICTOREM_ARTFLOW_KEY` — Your ArtFlowKey, issued on request through your Pictorem account (can be a test-mode key).

## Run

    uvx platform-mcp-hub serve pictorem          # Python
    npx -y platform-mcp-hub serve pictorem       # TypeScript
    claude mcp add pictorem -- uvx platform-mcp-hub serve pictorem

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pictorem-mcp`. Python and TypeScript serve identical tools.

# Doba MCP server

Category: **ecommerce_suppliers** · Docs: https://open.doba.com/apidoc/retailer/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/doba.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/pay/payManage/doba/queryPrepayBalance` (https://open.doba.com/apidoc/retailer/guide)
- `list_products` — `GET /api/goods/doba/spu/list` (https://open.doba.com/apidoc/retailer/guide)
- `get_product` — `GET /api/goods/doba/spu/detail` (https://open.doba.com/apidoc/retailer/guide)
- `quote_shipping` — `POST /api/shipping/doba/cost/goods` (https://open.doba.com/apidoc/retailer/guide)
- `create_order` — `POST /api/order/doba/importOrder` (https://open.doba.com/apidoc/retailer/guide)
- `get_order` — `GET /api/order/doba/queryOrder` (https://open.doba.com/apidoc/retailer/guide)
- `track` — `POST /api/order/doba/queryLogisTrack` (https://open.doba.com/apidoc/retailer/guide)

## Credentials

- `PLATFORM_MCP_DOBA_APP_KEY` — appKey assigned by Doba (Retailer API > Generate Key, https://open.doba.com/apidoc/retailer/developer/key); sent as the appKey header.
- `PLATFORM_MCP_DOBA_PRIVATE_KEY` — Your RSA private key from the same page, as PEM: '-----BEGIN PRIVATE KEY-----' + the base64 PKCS#8 key Doba shows + '-----END PRIVATE KEY-----' (newlines may be written as \n). Signs 'appKey=…&signType=rsa2&timestamp=…' with SHA256withRSA; never sent on the wire.
- `PLATFORM_MCP_DOBA_PLATFORM_ID` — Doba dsPlatformId of the marketplace your orders come from (Import Order): 1 Amazon, 2 eBay, 3 Shopify, 7 BigCommerce, 8 WooCommerce, 13 Walmart, 19 TikTok Shop, 26 Etsy, 99 Others (https://open.doba.com/apidoc/retailer).

## Run

    uvx platform-mcp-hub serve doba          # Python
    npx -y platform-mcp-hub serve doba       # TypeScript
    claude mcp add doba -- uvx platform-mcp-hub serve doba

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/doba-mcp`. Python and TypeScript serve identical tools.

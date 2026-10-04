# Sunsky Online MCP server

Category: **ecommerce_suppliers** · Docs: https://doc.sunsky-online.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/sunsky_online.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /openapi/order!getBalance.do` (https://doc.sunsky-online.com/check-your-balance-on-sunsky-425439187e0)
- `list_products` — `POST /openapi/product!search.do` (https://doc.sunsky-online.com/search-products-425439176e0)
- `get_product` — `POST /openapi/product!detail.do` (https://doc.sunsky-online.com/get-the-product-details-425439177e0)
- `quote_shipping` — `POST /openapi/order!getPricesAndFreights.do` (https://doc.sunsky-online.com/get-the-prices-and-the-shipping-costs-for-the-items-425439181e0)
- `create_order` — `POST /openapi/order!createOrder.do` (https://doc.sunsky-online.com/create-an-order-425439182e0)
- `get_order` — `POST /openapi/order!getOrderDetails.do` (https://doc.sunsky-online.com/get-the-order-details-425439184e0)
- `track` — `POST /openapi/order!getOrderDetails.do` (https://doc.sunsky-online.com/get-the-order-details-425439184e0)

## Credentials

- `PLATFORM_MCP_SUNSKY_ONLINE_KEY` — SUNSKY Open API key, issued by your SUNSKY sales manager (https://doc.sunsky-online.com/).
- `PLATFORM_MCP_SUNSKY_ONLINE_SECRET` — SUNSKY Open API secret issued with the key; signs every call (MD5 of the parameter values sorted by name, then '@' + secret) and is never sent.
- `PLATFORM_MCP_SUNSKY_ONLINE_LANGUAGE` — Product text language code (Appendix E), e.g. en, fr, de, es, it, zh_CN; default en.

## Run

    uvx platform-mcp-hub serve sunsky_online          # Python
    npx -y platform-mcp-hub serve sunsky_online       # TypeScript
    claude mcp add sunsky_online -- uvx platform-mcp-hub serve sunsky_online

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/sunsky_online-mcp`. Python and TypeScript serve identical tools.

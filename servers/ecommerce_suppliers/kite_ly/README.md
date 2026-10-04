# Kite (Prodigi Group) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.kite.ly/docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/kite_ly.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v4.0/order/` (https://www.kite.ly/docs/#getting-a-list-of-orders)
- `create_order` — `POST /v4.0/print/` (https://www.kite.ly/docs/#placing-orders)
- `get_order` — `GET /v4.0/order/{id}` (https://www.kite.ly/docs/#orders)
- `track` — `GET /v4.0/order/{order_id}` (https://www.kite.ly/docs/#orders)
- ~~`list_products`~~ not offered: The docs show GET /v4.1/template/?limit=10 only as an authentication example without documenting its response; products are the template_ids listed in the ordering sections.
- ~~`get_product`~~ not offered: No documented single-product endpoint; product identifiers and options are documented as template_id tables per product family.
- ~~`quote_shipping`~~ not offered: GET /v4.0/shipping_methods/{template_id} answers shipping_regions keyed by Kite region codes (e.g. ROW) with shipping_classes[{class_name, costs[{amount, currency}]}]; the vocabulary's country cannot select the region.

## Credentials

- `PLATFORM_MCP_KITE_LY_API_KEY_PAIR` — Your Kite API key and secret key joined by a colon, exactly as the Authorization header expects them: <public_key>:<secret_key> (dashboard > credentials). The secret key is required for order requests, which are then charged to the card on your Kite account; test-mode keys never create real products.

## Run

    uvx platform-mcp-hub serve kite_ly          # Python
    npx -y platform-mcp-hub serve kite_ly       # TypeScript
    claude mcp add kite_ly -- uvx platform-mcp-hub serve kite_ly

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kite_ly-mcp`. Python and TypeScript serve identical tools.

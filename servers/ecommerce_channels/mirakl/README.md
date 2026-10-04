# Mirakl-powered marketplaces MCP server

Category: **ecommerce_channels** · Docs: https://developer.mirakl.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/mirakl.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/account` (https://developer.mirakl.com/content/product/mmp/rest/seller/openapi3/stores/a01)
- `list_orders` — `GET /api/orders` (https://developer.mirakl.com/content/product/mmp/rest/seller/openapi3/orders/or11)
- `mark_shipped` — `PUT /api/orders/{order_id}/tracking` (https://developer.mirakl.com/content/product/mmp/rest/seller/openapi3/orders/or23)
- ~~`create_listing`~~ not offered: OF24 POST /api/offers requires product_id + product_id_type (the marketplace product the offer attaches to) and state_code for every offer ('Required at offer creation'); the vocabulary has no product reference or offer condition.
- ~~`update_listing`~~ not offered: OF24 POST /api/offers is the only JSON offer write and replaces the whole offer: 'You must send all offer fields. Offer fields that are not sent are reset to their default value' (quantity 'if not provided, will be set to 0', description deleted), so a partial update would wipe the offer.
- ~~`end_listing`~~ not offered: Offers are deleted through OF24 with update_delete=delete, whose schema still requires price, product_id, product_id_type and state_code for the offer; the vocabulary only carries the listing id.
- ~~`set_inventory`~~ not offered: Stock-only updates are STO01 (multipart CSV stock file import) or a full OF24 offer replacement ('quantity ... if not provided, will be set to 0' and every other unsent field reset); neither is a single JSON stock call.

## Credentials

- `PLATFORM_MCP_MIRAKL_API_KEY` — Shop API key generated in the marketplace's Mirakl seller back office (user menu > API key > Generate); sent verbatim as the Authorization header (no Bearer prefix).
- `PLATFORM_MCP_MIRAKL_INSTANCE_HOST` — Host of your marketplace's Mirakl instance without scheme, e.g. marketplace.example.com or <operator>.mirakl.net (the operator gives it with the API key); every call goes to https://<instance_host>/api/...
- `PLATFORM_MCP_MIRAKL_SHOP_ID` — Numeric shop id, only when your API key's user has access to several shops (sent as ?shop_id= on every call; the default shop is used otherwise).

## Run

    uvx platform-mcp-hub serve mirakl          # Python
    npx -y platform-mcp-hub serve mirakl       # TypeScript
    claude mcp add mirakl -- uvx platform-mcp-hub serve mirakl

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mirakl-mcp`. Python and TypeScript serve identical tools.

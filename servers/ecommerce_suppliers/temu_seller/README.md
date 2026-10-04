# Temu Seller Center MCP server

Category: **ecommerce_suppliers** · Docs: https://seller.temu.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/temu_seller.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /openapi/router` (https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a&sub_menu_code=93de550b56c8417caccb88824be3e614)
- `list_products` — `POST /openapi/router` (https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a)
- `get_product` — `POST /openapi/router` (https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a)
- `get_order` — `POST /openapi/router` (https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a)
- ~~`quote_shipping`~~ not offered: Temu is a sales channel: the seller ships Temu's buyer orders; the Partner Platform (https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a) has no API that quotes shipping for buying goods.
- ~~`create_order`~~ not offered: Orders are placed by Temu shoppers; the Order APIs (bg.order.list.v2.get, bg.order.detail.v2.get, … in https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a) read them and no API creates one.
- ~~`track`~~ not offered: Tracking is written by the seller through the Fulfillment APIs (bg.logistics.shipment.* in https://partner.temu.com/documentation?menu_code=fb16b05f7a904765aac4af3a24b87d4a); a buyer-side tracking read for an order id alone is not documented.

## Credentials

- `PLATFORM_MCP_TEMU_SELLER_APP_KEY` — app_key of your TEMU Partner Platform app (partner.temu.com > App management).
- `PLATFORM_MCP_TEMU_SELLER_APP_SECRET` — app_secret of the same app; signs every call (upper-case MD5 of app_secret + body parameters sorted by name as name+value + app_secret) and is never sent.
- `PLATFORM_MCP_TEMU_SELLER_ACCESS_TOKEN` — The store's access_token from the Seller Center authorisation (Seller Center > open platform > authorise app, or bg.open.accesstoken.create with the callback code); valid about one year (see expiredTime from me).
- `PLATFORM_MCP_TEMU_SELLER_REGION` — API host region of the store: us (United States), eu (EU/UK sites) or global (Mexico, Japan, …) → https://openapi-b-<region>.temu.com/openapi/router.

## Run

    uvx platform-mcp-hub serve temu_seller          # Python
    npx -y platform-mcp-hub serve temu_seller       # TypeScript
    claude mcp add temu_seller -- uvx platform-mcp-hub serve temu_seller

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/temu_seller-mcp`. Python and TypeScript serve identical tools.

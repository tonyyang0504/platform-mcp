# Temu MCP server

Category: **ecommerce_channels** · Docs: https://partner-us.temu.com/documentation · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/temu.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /openapi/router` (https://partner-us.temu.com/documentation?menu_code=93de550b56c8417caccb88824be3e614)
- `list_orders` — `POST /openapi/router` (https://partner-us.temu.com/documentation?menu_code=554fd46b45ee49269cbdd6d4008a5dc1)
- `set_inventory` — `POST /openapi/router` (https://partner-us.temu.com/documentation?menu_code=429ffa60b265451d9421cd5a2004eeef)
- `end_listing` — `POST /openapi/router` (https://partner-us.temu.com/documentation?menu_code=97853cce1f5140e0aa302b5e530a8c99)
- ~~`create_listing`~~ not offered: bg.local.goods.add / temu.local.goods.v3.add (https://partner-us.temu.com/documentation?menu_code=645953235e964a23a0320b249ba865af) require a leaf category id, category-specific properties, a shipping template and SKU spec ids obtained from bg.local.goods.cats.get / bg.local.goods.spec.id.get; the vocabulary's create_listing has none of these inputs.
- ~~`update_listing`~~ not offered: Prices change only through bg.local.goods.priceorder.change.sku.price, which needs per-SKU 'skuId' (required) and 'newSupplierPrice {amount, currency}' and 'Support merchants within the white list' (https://partner-us.temu.com/documentation?menu_code=dbf95d09e514491f8685013824cecc76); update_listing has no SKU or currency input.
- ~~`mark_shipped`~~ not offered: bg.logistics.shipment.v2.confirm (https://partner-us.temu.com/documentation?menu_code=70cca1a3690044eaae4a28de6de76bb1) requires, per package, 'selfShippingWarehouseId' (required) and 'orderSendInfoList' with each child 'orderSn' and 'quantity' (required) besides the carrierId and trackingNumber; mark_shipped only has order_id, carrier and tracking_number.

## Credentials

- `PLATFORM_MCP_TEMU_APP_KEY` — app_key of your Temu Partner Platform app (issued after app review).
- `PLATFORM_MCP_TEMU_APP_SECRET` — app_secret of the same app; signs every call: upper(MD5(app_secret + sorted key+value of all body fields + app_secret)). Never sent on the wire.
- `PLATFORM_MCP_TEMU_ACCESS_TOKEN` — The store's access_token, issued when the seller authorises your app in Seller Center (manual authorisation copies it; 'can be obtained from Seller Center', Common Parameters). Check its expiry with `me` (result.expiredTime).
- `PLATFORM_MCP_TEMU_REGION` — Gateway of the seller's store: us (United States), eu (Germany, Italy, France, Spain, UK, …) or global (Mexico, Japan, …) → https://openapi-b-{region}.temu.com/openapi/router ('Endpoints and Request Method', Developer Guide).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve temu   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve temu
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve temu   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/temu-mcp`. Python and TypeScript serve identical tools.

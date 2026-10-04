# Falabella Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://developers.falabella.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/falabella.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /` (https://developers.falabella.com/docs/products/getproducts)
- `list_orders` — `GET /` (https://developers.falabella.com/docs/orders/getorders)
- `update_listing` — `POST /` (https://developers.falabella.com/docs/products/productupdate)
- `set_inventory` — `POST /` (https://developers.falabella.com/docs/products/updatestock)
- `end_listing` — `POST /` (https://developers.falabella.com/docs/products/productremove)
- ~~`create_listing`~~ not offered: ProductCreate (https://developers.falabella.com/docs/products/productcreate) requires Brand, PrimaryCategory, the category's mandatory ProductData attributes (ConditionType, PackageHeight/Width/Length/Weight, TaxPercentage in Colombia) and a Variation group; the vocabulary carries none of them.
- ~~`mark_shipped`~~ not offered: SetStatusToReadyToShip (https://developers.falabella.com/docs/orders/setstatustoreadytoship) takes "OrderItemIds=[1,2,3]" and a PackageId, not an order id, and the carrier/tracking come from Falabella's label; order-item ids are not a vocabulary input.

## Credentials

- `PLATFORM_MCP_FALABELLA_API_KEY` — Seller Center API key (Mi Cuenta > Integraciones / API in Falabella Seller Center). Signs every request (HMAC-SHA256 hex over the name-sorted, RFC 3986-encoded query, sent as the Signature parameter); never sent on the wire.
- `PLATFORM_MCP_FALABELLA_USER_ID` — Seller Center UserID: the e-mail login the API key belongs to (sent as UserID).
- `PLATFORM_MCP_FALABELLA_OPERATOR_CODE` — Business unit to write to: facl (Chile), fape (Peru) or faco (Colombia).
- `PLATFORM_MCP_FALABELLA_WAREHOUSE_ID` — SellerWarehouseId for set_inventory when the seller has several warehouses (GetWarehouse); leave empty with a single warehouse.

## Run

    uvx platform-mcp-hub serve falabella          # Python
    npx -y platform-mcp-hub serve falabella       # TypeScript
    claude mcp add falabella -- uvx platform-mcp-hub serve falabella

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/falabella-mcp`. Python and TypeScript serve identical tools.

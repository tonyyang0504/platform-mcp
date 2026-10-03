# Trendyol Gulf MCP server

Category: **ecommerce_channels** · Docs: https://developers.trendyol.com/en · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/trendyol_gulf.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sellers/{sid}/addresses` (https://developers.trendyol.com/v2.0/docs/return-and-shipping-address-information-getsuppliersaddresses)
- `update_listing` — `POST /inventory/sellers/{sid}/products/price-and-inventory` (https://developers.trendyol.com/v2.0/docs/stock-and-price-update-updatepriceandinventory-1)
- `set_inventory` — `POST /inventory/sellers/{sid}/products/price-and-inventory` (https://developers.trendyol.com/v2.0/docs/stock-and-price-update-updatepriceandinventory-1)
- `end_listing` — `PUT /product/sellers/{sid}/products/archive-state` (https://developers.trendyol.com/v2.0/docs/product-archive)
- `list_orders` — `GET /order/sellers/{sid}/v2/orders` (https://developers.trendyol.com/v2.0/docs/get-order-packages-getshipmentpackages)
- ~~`create_listing`~~ not offered: Product creation (createProducts v2) needs categoryId, brandId, category attributes, cargo company and shipment/return address ids, VAT rate and images per barcode, and goes through Trendyol approval; the vocabulary has no category, brand or attribute inputs.
- ~~`mark_shipped`~~ not offered: Shipping uses the Trendyol-contracted cargo provider assigned to the package (cargoTrackingNumber is created by Trendyol); the seller only reports package statuses with updatePackage (Picking, then Invoiced with lines[{lineId, quantity}] and an invoice number) — there is no seller call that submits a carrier and tracking number for an order.

## Credentials

- `PLATFORM_MCP_TRENDYOL_GULF_API_KEY` — API KEY from Seller Center > Hesap Bilgilerim / Account Information > Entegrasyon Bilgileri / Integration Information (visible to the master/admin user only; PROD and STAGE differ); HTTP Basic username.
- `PLATFORM_MCP_TRENDYOL_GULF_API_SECRET` — API SECRET KEY from the same page; HTTP Basic password.
- `PLATFORM_MCP_TRENDYOL_GULF_SELLER_ID` — Your Trendyol seller (supplier) ID from the same Integration Information page; used in every path.
- `PLATFORM_MCP_TRENDYOL_GULF_USER_AGENT` — Mandatory User-Agent (requests without it get 403): '<sellerId> - SelfIntegration' for your own software, or '<sellerId> - <IntegratorName>' (alphanumeric, max 30 characters) when an integrator company runs it, e.g. '1234 - SelfIntegration'.
- `PLATFORM_MCP_TRENDYOL_GULF_API_HOST` — apigw.trendyol.com (PROD) or stageapigw.trendyol.com (STAGE, IP-authorised test environment).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve trendyol_gulf   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve trendyol_gulf
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve trendyol_gulf   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/trendyol_gulf-mcp`. Python and TypeScript serve identical tools.

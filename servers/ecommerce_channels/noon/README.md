# noon MCP server

Category: **ecommerce_channels** · Docs: https://noon-docs.noonpartners.dev/docs/getting-started/intro · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/noon.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /identity/v1/whoami` (https://noon-docs.noonpartners.dev/docs/api-reference/authentication/auth-service-whoami)
- `update_listing` — `POST /pricing/v1/pricing/upsert` (https://noon-docs.noonpartners.dev/docs/api-reference/pricing/pricing-service-batch-upsert-pricing)
- `end_listing` — `POST /pricing/v1/pricing/upsert` (https://noon-docs.noonpartners.dev/docs/api-reference/pricing/pricing-service-batch-upsert-pricing)
- `set_inventory` — `POST /stock/v1/stock-update` (https://noon-docs.noonpartners.dev/docs/api-reference/stock/stock-service-update-stock)
- `list_orders` — `POST /fbpi/v1/fbpi-orders/list` (https://noon-docs.noonpartners.dev/docs/api-reference/fbpi/fbpi-service-list-fbpi-orders)
- ~~`create_listing`~~ not offered: UpsertProduct requires 'brand (string, required)', 'category (string, required)', 'images' and an 'attributes (object map, required)' per category (https://noon-docs.noonpartners.dev/docs/api-reference/content/content-service-upsert-product); the vocabulary's create_listing has no brand, category or attributes.
- ~~`mark_shipped`~~ not offered: CreateShipment needs 'integration_shipment_nr (string, required)' and 'items (object[], required)' with each 'mp_item_nr' of the order (https://noon-docs.noonpartners.dev/docs/api-reference/fbpi/fbpi-service-create-shipment); mark_shipped carries only order_id, carrier and tracking_number.

## Credentials

- `PLATFORM_MCP_NOON_KEY_ID` — key_id from your noon service-account key file (.json), created in the noon Partner portal.
- `PLATFORM_MCP_NOON_PRIVATE_KEY` — private_key (PEM) from the same service-account key file; it signs the RS256 login JWT.
- `PLATFORM_MCP_NOON_PROJECT_CODE` — project_code from the key file, sent as default_project_code at login.
- `PLATFORM_MCP_NOON_WAREHOUSE_CODE` — Integration warehouse code for stock updates and FBPI order listing (see ListWarehouses).
- `PLATFORM_MCP_NOON_COUNTRY_CODE` — Marketplace country code for pricing (e.g. ae, sa, eg).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve noon   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve noon
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve noon   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/noon-mcp`. Python and TypeScript serve identical tools.

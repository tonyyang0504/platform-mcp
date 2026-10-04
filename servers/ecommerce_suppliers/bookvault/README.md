# Bookvault (CopyTECH (UK) Ltd t/a Printondemand-worldwide) MCP server

Category: **ecommerce_suppliers** · Docs: https://help.bookvault.app/api-setup · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/bookvault.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v4/account` (https://api.bookvault.app/docs.html)
- `list_products` — `GET /v4/titles` (https://api.bookvault.app/docs.html)
- `get_product` — `GET /v4/title/{id}` (https://api.bookvault.app/docs.html)
- `create_order` — `POST /v4/order` (https://api.bookvault.app/docs.html)
- `get_order` — `GET /v4/order` (https://api.bookvault.app/docs.html)
- ~~`quote_shipping`~~ not offered: POST /v4/dispatch requires areaCode (the delivery postcode), shipmentDate, currency and serviceLevel besides orderLines and countryCode, and GET /v4/dispatch needs the parcel weight and partner; the vocabulary's product_id/country/quantity cannot supply the postcode or date.
- ~~`track`~~ not offered: No tracking-events endpoint: the order record carries a single fulfillment.trackingDetails {trackingNumber, combinedURL, servName} (see get_order's tracking_number/tracking_url).

## Credentials

- `PLATFORM_MCP_BOOKVAULT_API_KEY` — Bookvault API key from the portal's Apps page (Bookvault API > Generate Credentials; shown once), sent as `Authorization: basic <key>`. Supply the key exactly as displayed, starting with bv_.
- `PLATFORM_MCP_BOOKVAULT_PARTNER` — Print partner for create_order (required by Bookvault): Bookvault_UK, Bookvault_US, Bookvault_AU or Bookvault_CA.

## Run

    uvx platform-mcp-hub serve bookvault          # Python
    npx -y platform-mcp-hub serve bookvault       # TypeScript
    claude mcp add bookvault -- uvx platform-mcp-hub serve bookvault

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bookvault-mcp`. Python and TypeScript serve identical tools.

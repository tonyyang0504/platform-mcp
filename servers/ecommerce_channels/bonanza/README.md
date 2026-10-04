# Bonanza MCP server

Category: **ecommerce_channels** · Docs: https://api.bonanza.com/docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/bonanza.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /api_requests/secure_request` (https://api.bonanza.com/docs/reference/get_token_status)
- `create_listing` — `POST /api_requests/secure_request` (https://api.bonanza.com/docs/reference/add_fixed_price_item)
- `end_listing` — `POST /api_requests/secure_request` (https://api.bonanza.com/docs/reference/end_fixed_price_item)
- `list_orders` — `POST /api_requests/secure_request` (https://api.bonanza.com/docs/reference/get_orders)
- `mark_shipped` — `POST /api_requests/secure_request` (https://api.bonanza.com/docs/reference/complete_sale)
- ~~`update_listing`~~ not offered: reviseFixedPriceItem documents only itemId and discardOldVariations as inputs (https://api.bonanza.com/docs/reference/revise_fixed_price_item); which item fields it accepts is not documented. Price/quantity changes go through updateInventory, whose body is keyed by the item id itself ('updates.itemId.price') — an object key built from an argument, which the declarative body cannot express.
- ~~`set_inventory`~~ not offered: updateInventory takes 'updates.itemId.quantity', i.e. a JSON object whose KEY is the item id ({"updates": {"<itemId>": {"quantity": n}}}); the declarative body builds only fixed keys, and there is no SKU-addressed stock call.

## Credentials

- `PLATFORM_MCP_BONANZA_DEV_ID` — Developer id (dev_id) of your approved Bonanza API account (api.bonanza.com > Apply for an API account); sent as the X-BONANZLE-API-DEV-NAME header.
- `PLATFORM_MCP_BONANZA_CERT_ID` — Certificate id (cert_id) of the same API account; sent as the X-BONANZLE-API-CERT-NAME header.
- `PLATFORM_MCP_BONANZA_AUTH_TOKEN` — The seller's verified user token (fetchToken, then the seller approves it at the returned authentication URL); sent in every request body as requesterCredentials.bonanzleAuthToken. Tokens expire a year after issue or when the seller deactivates them.

## Run

    uvx platform-mcp-hub serve bonanza          # Python
    npx -y platform-mcp-hub serve bonanza       # TypeScript
    claude mcp add bonanza -- uvx platform-mcp-hub serve bonanza

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bonanza-mcp`. Python and TypeScript serve identical tools.

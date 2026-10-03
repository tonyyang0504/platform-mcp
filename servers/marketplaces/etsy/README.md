# Etsy MCP server

Category: **marketplaces** · Docs: https://developers.etsy.com · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/etsy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.etsy.com/documentation/reference#operation/getMe)
- `list_products` — `GET /shops/{shop_id}/listings` (https://developers.etsy.com/documentation/reference#operation/getListingsByShop)
- `get_product` — `GET /listings/{product_id}` (https://developers.etsy.com/documentation/reference#operation/getListing)
- `create_product` — `POST /shops/{shop_id}/listings` (https://developers.etsy.com/documentation/reference#operation/createDraftListing)
- `list_sales` — `GET /shops/{shop_id}/transactions` (https://developers.etsy.com/documentation/reference#operation/getShopReceiptTransactionsByShop)
- ~~`update_price`~~ not offered: Listing prices live in the inventory offerings: updateListingInventory (PUT /v3/application/listings/{listing_id}/inventory) must resend the entire products array with every offering's price, quantity and is_enabled (https://developers.etsy.com/documentation/reference#operation/updateListingInventory), which one call from a product id and price cannot build.
- ~~`get_sales_stats`~~ not offered: Open API v3 has no revenue summary; the payment ledger (getShopPaymentAccountLedgerEntries) lists individual entries between required min_created / max_created epoch bounds (https://developers.etsy.com/documentation/reference#operation/getShopPaymentAccountLedgerEntries).
- ~~`list_refunds`~~ not offered: There is no refunds collection; refunds appear inside each ShopReceipt's refunds[] (https://developers.etsy.com/documentation/reference#operation/getShopReceipts).
- ~~`refund`~~ not offered: The Open API v3 reference has no refund operation; refunds are issued in Shop Manager (https://developers.etsy.com/documentation/reference).

## Credentials

- `PLATFORM_MCP_ETSY_CLIENT_ID` — Etsy App API Key keystring (etsy.com/developers/your-apps); sent as client_id in the refresh grant form body (Etsy's refresh grant takes no client secret).
- `PLATFORM_MCP_ETSY_API_KEY` — Value of the x-api-key header required on every v3 request: the keystring and the shared secret joined by a colon, e.g. 1aa2bb33c44d55eeeeee6fff:a1b2c3d4e5 (both on the Your Apps page).
- `PLATFORM_MCP_ETSY_REFRESH_TOKEN` — Refresh token (numeric user id prefix, e.g. 12345678.JNGI...) from a one-time OAuth 2.0 authorization-code + PKCE consent at etsy.com/oauth/connect with scopes shops_r listings_r listings_w transactions_r; valid 90 days, after which the seller consents again. Access tokens (1 h) are minted from it. A refresh grant also returns a new refresh token, which replaces the old one. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. The state file is keyed by platform id, so it is shared with ecommerce_channels/etsy: give each server its own PLATFORM_MCP_STATE_DIR (or its own consent) so they never race on one rotating refresh token.
- `PLATFORM_MCP_ETSY_SHOP_ID` — Numeric Etsy shop id (GET /v3/application/users/me returns it as shop_id).
- `PLATFORM_MCP_ETSY_TAXONOMY_ID` — Seller taxonomy id every created listing is filed under (GET /v3/application/seller-taxonomy/nodes); required by create_product.
- `PLATFORM_MCP_ETSY_WHO_MADE` — createDraftListing who_made for new listings: i_did | someone_else | collective; required by create_product.
- `PLATFORM_MCP_ETSY_WHEN_MADE` — createDraftListing when_made for new listings, e.g. made_to_order, 2020_2026, 2010_2019, before_2007; required by create_product.
- `PLATFORM_MCP_ETSY_SHIPPING_PROFILE_ID` — Shipping profile id for new physical listings (GET /v3/application/shops/{shop_id}/shipping-profiles); required for physical listings.
- `PLATFORM_MCP_ETSY_READINESS_STATE_ID` — Processing profile id for new physical listings (GET /v3/application/shops/{shop_id}/readiness-state-definitions); required for physical listings.
- `PLATFORM_MCP_ETSY_RETURN_POLICY_ID` — Optional return policy id for new listings (GET /v3/application/shops/{shop_id}/policies/return).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve marketplaces/etsy   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve marketplaces/etsy
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve marketplaces/etsy   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/etsy-marketplaces-mcp`. Python and TypeScript serve identical tools.

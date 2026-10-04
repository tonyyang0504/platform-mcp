# Lulu Print API (Lulu Direct) (cross-ref lulu_print_api in Books & media) MCP server

Category: **ecommerce_suppliers** · Docs: https://api.lulu.com/docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/lulu.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /print-jobs/statistics/` (https://api.lulu.com/docs/#tag/Print-Jobs)
- `create_order` — `POST /print-jobs/` (https://api.lulu.com/docs/#tag/Print-Jobs/operation/Print-Jobs_create)
- `get_order` — `GET /print-jobs/{id}/` (https://api.lulu.com/docs/#tag/Print-Jobs)
- `track` — `GET /print-jobs/{order_id}/status/` (https://api.lulu.com/docs/#section/Shipping-Notification)
- ~~`list_products`~~ not offered: No product catalogue endpoint: printables are defined per Print-Job by a pod_package_id (trim size, colour, paper, binding) chosen with Lulu's product spec sheet / pricing calculator, not listed through the API.
- ~~`get_product`~~ not offered: No product endpoint (see list_products); cover dimensions and file validation endpoints exist but describe files, not products.
- ~~`quote_shipping`~~ not offered: POST /shipping-options/ requires line_items[{pod_package_id, page_count, quantity}] and page_count (the book's page count) has no counterpart in the vocabulary's product_id/country/quantity input.

## Credentials

- `PLATFORM_MCP_LULU_CLIENT_ID` — Client key of your Lulu Print API account (developers.lulu.com > API Keys); sent with the secret as HTTP Basic on the client-credentials token request.
- `PLATFORM_MCP_LULU_CLIENT_SECRET` — Client secret from the same page. Sandbox keys belong to https://api.sandbox.lulu.com, which this server does not switch to.
- `PLATFORM_MCP_LULU_CONTACT_EMAIL` — contact_email sent with create_order (required by POST /print-jobs/): who Lulu contacts about the Print-Job.
- `PLATFORM_MCP_LULU_ENV` — Vendor environment (default production): sandbox = https://api.sandbox.lulu.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_LULU_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve lulu          # Python
    npx -y platform-mcp-hub serve lulu       # TypeScript
    claude mcp add lulu -- uvx platform-mcp-hub serve lulu

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lulu-mcp`. Python and TypeScript serve identical tools.

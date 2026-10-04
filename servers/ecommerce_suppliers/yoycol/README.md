# Yoycol MCP server

Category: **ecommerce_suppliers** · Docs: https://www.yoycol.com/api/2025/redoc · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/yoycol.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/2025/open/v4/catalog/products` (https://www.yoycol.com/api/2025/redoc)
- `list_products` — `GET /api/2025/open/v4/catalog/products` (https://www.yoycol.com/api/2025/redoc)
- `get_product` — `GET /api/2025/open/v4/catalog/products/{id}` (https://www.yoycol.com/api/2025/redoc)
- `quote_shipping` — `GET /api/2025/open/v4/shipping/sku_quotes` (https://www.yoycol.com/api/2025/redoc)
- ~~`create_order`~~ not offered: POST /api/2025/open/v4/orders has no query string, and the V4 signatureData appends '\nparams=<sorted query>' only 'if (paramStr)' (Signature Guide, https://www.yoycol.com/api/2025/redoc, Docs Guide section); the runtime's sign payload is one fixed template, so a request with no query string would be signed with a trailing empty params line and rejected.
- ~~`get_order`~~ not offered: GET /api/2025/open/v4/orders/{orderId} has no query parameters, and the V4 signatureData appends '\nparams=<sorted query>' only 'if (paramStr)' (Signature Guide, https://www.yoycol.com/api/2025/redoc, Docs Guide section); the runtime's sign payload is one fixed template, so a request with no query string would be signed with a trailing empty params line and rejected.
- ~~`track`~~ not offered: GET /api/2025/open/v4/orders/{orderId}/tracking has no query parameters, and the V4 signatureData appends '\nparams=<sorted query>' only 'if (paramStr)' (Signature Guide, https://www.yoycol.com/api/2025/redoc, Docs Guide section); the runtime's sign payload is one fixed template, so a request with no query string would be signed with a trailing empty params line and rejected.

## Credentials

- `PLATFORM_MCP_YOYCOL_ACCESS_KEY` — accessKey issued by Yoycol for OPEN API V4 (sent as X-API-Access-Key).
- `PLATFORM_MCP_YOYCOL_SECRET_KEY` — secretKey issued with it; signs every request (Base64 HMAC-SHA256 over method, path, timestamp, nonce, accessKey, algorithm, version and the sorted query). Never sent on the wire.

## Run

    uvx platform-mcp-hub serve yoycol          # Python
    npx -y platform-mcp-hub serve yoycol       # TypeScript
    claude mcp add yoycol -- uvx platform-mcp-hub serve yoycol

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yoycol-mcp`. Python and TypeScript serve identical tools.

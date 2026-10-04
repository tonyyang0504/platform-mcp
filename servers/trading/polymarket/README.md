# Polymarket (public markets) MCP server

Category: **trading** · Docs: https://docs.polymarket.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/polymarket.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /status` (https://docs.polymarket.com/api-reference/markets/list-markets)
- `list_markets` — `GET /markets` (https://docs.polymarket.com/api-reference/markets/list-markets)
- `get_ticker` — `GET /markets/slug/{symbol}` (https://docs.polymarket.com/api-reference/markets/get-market-by-slug)
- ~~`get_candles`~~ not offered: GET /prices-history (CLOB) returns only {t, p} price points per outcome token, not open/high/low/close candles.
- ~~`get_balances`~~ not offered: CLOB balance-allowance needs L2 headers whose POLY_SIGNATURE is 'urlsafeBase64WithPadding(HMAC-SHA256(base64Decode(<clob_api_secret>), message))' (docs); the runtime keys HMAC with the secret's raw text and emits standard base64, so the signature cannot be produced.
- ~~`list_orders`~~ not offered: GET /data/orders needs the same L2 HMAC headers keyed by the base64-decoded secret with a URL-safe base64 signature, which the runtime's sign block cannot express.
- ~~`place_order`~~ not offered: Orders are EIP-712 typed-data structs signed by the wallet's private key (L1) before being posted with L2 HMAC headers (docs: 'Create an L1 Signature … to attest to ownership of the signer'); the runtime has no wallet signer.
- ~~`cancel_order`~~ not offered: DELETE /order needs L2 HMAC headers keyed by the base64-decoded API secret with a URL-safe base64 signature, which the runtime's sign block cannot express.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve polymarket          # Python
    npx -y platform-mcp-hub serve polymarket       # TypeScript
    claude mcp add polymarket -- uvx platform-mcp-hub serve polymarket

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/polymarket-mcp`. Python and TypeScript serve identical tools.

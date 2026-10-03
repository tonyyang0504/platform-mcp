# Hyperliquid (perpetuals) MCP server

Category: **trading** · Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/hyperliquid.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- `list_markets` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- `get_ticker` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)
- `list_orders` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)
- ~~`get_candles`~~ not offered: candleSnapshot requires req.startTime and req.endTime in milliseconds (docs: both required); the vocabulary carries no time range and the runtime has no millisecond clock expression, so a latest-N request cannot be built.
- ~~`get_balances`~~ not offered: clearinghouseState reports perp margin as one marginSummary object plus assetPositions (positions), not per-asset balance rows; spot balances are served by hyperliquid_spot.
- ~~`place_order`~~ not offered: orders and cancels go through POST /exchange with an EIP-712 typed-data signature produced by the wallet's secp256k1 private key (docs: 'signing … is done with the private key of the agent or main wallet'); the runtime only has HMAC request signing, so writes are not offered
- ~~`cancel_order`~~ not offered: orders and cancels go through POST /exchange with an EIP-712 typed-data signature produced by the wallet's secp256k1 private key (docs: 'signing … is done with the private key of the agent or main wallet'); the runtime only has HMAC request signing, so writes are not offered

## Credentials

- `PLATFORM_MCP_HYPERLIQUID_WALLET_ADDRESS` — Public 0x address (42 hex characters) of the MAIN wallet whose orders/balances to read. Not a secret; no private key is needed or accepted. Only list_orders/get_balances use it.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hyperliquid   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hyperliquid
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hyperliquid   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hyperliquid-mcp`. Python and TypeScript serve identical tools.

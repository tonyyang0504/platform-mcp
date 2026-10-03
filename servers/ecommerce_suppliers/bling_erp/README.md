# Bling ERP (BR integration hub — not a supplier) MCP server

Category: **ecommerce_suppliers** · Docs: https://developer.bling.com.br/home · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/bling_erp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /empresas/me/dados-basicos` (https://developer.bling.com.br/referencia)
- `list_products` — `GET /produtos` (https://developer.bling.com.br/referencia)
- `get_product` — `GET /produtos/{idProduto}` (https://developer.bling.com.br/referencia)
- `get_order` — `GET /pedidos/compras/{idPedidoCompra}` (https://developer.bling.com.br/referencia)
- ~~`quote_shipping`~~ not offered: Bling is an ERP; it has no carrier-rate endpoint for a product and destination (logistics endpoints manage shipping objects/labels of existing sales).
- ~~`create_order`~~ not offered: POST /pedidos/compras only records a purchase order inside Bling (fornecedor id, itens[{produto{id}, quantidade, valor}]); it is not transmitted to or paid at any supplier, and the vocabulary's shipping_address has no counterpart.
- ~~`track`~~ not offered: No tracking-events endpoint for purchase orders; logistics objects (GET /logisticas/objetos/{idObjeto}) belong to sales shipments and take an object id, not an order id.

## Credentials

- `PLATFORM_MCP_BLING_ERP_CLIENT_ID` — Client ID of your Bling app (Central de Extensões > Área do Integrador); sent with the client secret as HTTP Basic on the token request ('não é permitida a inserção destes parâmetros no body').
- `PLATFORM_MCP_BLING_ERP_CLIENT_SECRET` — Client Secret of the same Bling app.
- `PLATFORM_MCP_BLING_ERP_REFRESH_TOKEN` — refresh_token from a one-time authorization-code exchange (the code expires in 1 minute); valid 30 days. Access tokens last 6 hours (expires_in 21600) and are re-minted from it; a new refresh_token returned by Bling replaces the old one in memory, and with PLATFORM_MCP_STATE_DIR set it is also saved and preferred on the next start.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bling_erp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bling_erp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bling_erp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bling_erp-mcp`. Python and TypeScript serve identical tools.

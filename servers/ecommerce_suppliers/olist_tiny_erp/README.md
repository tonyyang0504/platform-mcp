# Olist Tiny ERP (BR integration hub — not a supplier) MCP server

Category: **ecommerce_suppliers** · Docs: https://api-docs.erp.olist.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/olist_tiny_erp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /info` (https://api-docs.erp.olist.com/api-reference/dados-da-empresa/obter-informações-da-conta-da-empresa)
- `list_products` — `GET /produtos` (https://api-docs.erp.olist.com/api-reference/produtos/listar-produtos)
- `get_product` — `GET /produtos/{id}` (https://api-docs.erp.olist.com/api-reference/produtos/obter-produto)
- `get_order` — `GET /ordem-compra/{id}` (https://api-docs.erp.olist.com/api-reference/ordem-de-compra/obter-ordem-de-compra)
- ~~`quote_shipping`~~ not offered: Olist ERP is an ERP; the v3 API (https://api.tiny.com.br/public-api/v3/swagger/swagger.json) has no carrier-rate endpoint for a product and destination.
- ~~`create_order`~~ not offered: POST /ordem-compra only records a purchase order inside the ERP (contato = supplier contact, itens[{produto{id}, quantidade, valor}]); it is not transmitted to or paid at any supplier, and the vocabulary's shipping_address has no counterpart.
- ~~`track`~~ not offered: No tracking endpoint for purchase orders; tracking data belongs to sales orders and invoices and the v3 API only writes it (PUT /pedidos/{idPedido}/despacho, PUT /notas/{idNota}/despacho 'Atualizar informações de rastreamento'), it does not expose it per purchase order.

## Credentials

- `PLATFORM_MCP_OLIST_TINY_ERP_CLIENT_ID` — Client ID of the API v3 app created in your Olist ERP (Tiny) account (Configurações > Aplicativos; https://api-docs.erp.olist.com/).
- `PLATFORM_MCP_OLIST_TINY_ERP_CLIENT_SECRET` — Client secret of the same app, sent in the token request body.
- `PLATFORM_MCP_OLIST_TINY_ERP_REFRESH_TOKEN` — refresh_token from the one-time authorization-code exchange (https://accounts.tiny.com.br/realms/tiny/protocol/openid-connect/auth ... then /token with grant_type=authorization_code). Access tokens expire after 4 hours and are re-minted from it; the refresh token 'tem duração de 1 dia' and each refresh returns a new one, which replaces it in memory (set PLATFORM_MCP_STATE_DIR to persist it across restarts).

## Run

    uvx platform-mcp-hub serve olist_tiny_erp          # Python
    npx -y platform-mcp-hub serve olist_tiny_erp       # TypeScript
    claude mcp add olist_tiny_erp -- uvx platform-mcp-hub serve olist_tiny_erp

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/olist_tiny_erp-mcp`. Python and TypeScript serve identical tools.

# Portal Nacional de Contratações Públicas MCP server

Category: **deals** · Docs: https://pncp.gov.br/api/consulta/swagger-ui/index.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/pncp_pncp_gov_br.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /v1/contratacoes/proposta` (https://pncp.gov.br/api/consulta/swagger-ui/index.html#/Contrata%C3%A7%C3%A3o/consultarContratacaoPeriodoRecebimentoPropostas)
- ~~`me`~~ not offered: Keyless consultation API; no account endpoint.
- ~~`get_posting`~~ not offered: The per-procurement call is GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}, which needs the three parts of numeroControlePNCP separately; the vocabulary's single id cannot be split, so re-read the record from the search hit.
- ~~`submit_bid`~~ not offered: PNCP only publishes procurements; proposals are submitted in the buyer's own system (linkSistemaOrigem).
- ~~`withdraw_bid`~~ not offered: No proposal API (see submit_bid).
- ~~`bid_status`~~ not offered: No proposal API; results appear later as atas/contratos in the consultation API.
- ~~`list_messages`~~ not offered: No messaging API in the consultation API.
- ~~`send_message`~~ not offered: No messaging API in the consultation API.
- ~~`credits`~~ not offered: No account or credit endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve pncp_pncp_gov_br   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve pncp_pncp_gov_br
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve pncp_pncp_gov_br   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pncp_pncp_gov_br-mcp`. Python and TypeScript serve identical tools.

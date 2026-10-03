# France Travail MCP server

Category: **jobs** · Docs: https://francetravail.io/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/france_travail.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /v2/offres/search` (https://francetravail.io/produits-partages/catalogue/offres-emploi/documentation)
- `get_posting` — `GET /v2/offres/{id}` (https://francetravail.io/produits-partages/catalogue/offres-emploi/documentation)
- ~~`me`~~ not offered: No account endpoint: the application authenticates with the client credentials grant ('Cinématique OAuth: client credentials grant', https://francetravail.io/produits-partages/documentation/utilisation-api-france-travail/generer-access-token) and the API only documents search, offer details and référentiels.
- ~~`apply`~~ not offered: No application endpoint: the offer detail says 'Pour postuler, utiliser le lien suivant: https://candidat.pole-emploi.fr/offres/recherche/detail/…' — candidates apply on the France Travail site.
- ~~`list_messages`~~ not offered: No messaging API is documented.

## Credentials

- `PLATFORM_MCP_FRANCE_TRAVAIL_CLIENT_ID` — Identifiant client of a francetravail.io application subscribed to the 'Offres d'emploi' API (create it at https://francetravail.io/inscription, then add the API to the application).
- `PLATFORM_MCP_FRANCE_TRAVAIL_CLIENT_SECRET` — Clé secrète of the same francetravail.io application.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve france_travail   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve france_travail
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve france_travail   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/france_travail-mcp`. Python and TypeScript serve identical tools.

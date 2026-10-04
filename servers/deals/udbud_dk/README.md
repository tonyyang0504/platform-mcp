# Udbud MCP server

Category: **deals** · Docs: https://udbud.dk/hjaelp/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/udbud_dk.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /ekstern-data/bekendtgoerelse/v1/fraKilde/DKUDBUD` (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml)
- `search_postings` — `GET /ekstern-data/bekendtgoerelse/v1/fraKilde/DKUDBUD` (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml)
- `get_posting` — `GET /ekstern-data/bekendtgoerelse/v1/{id}` (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml)
- ~~`submit_bid`~~ not offered: Tenders are submitted in the buyers' e-tendering systems; the Udbud.dk API only validates/publishes notices for system providers and syncs published notices (paths valider, publicer, {noticeId}/{noticeVersion}, fraKilde/{kilde} in https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml).
- ~~`withdraw_bid`~~ not offered: No bid operations exist in the Udbud.dk API (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml); bids are handled in the buyers' e-tendering systems.
- ~~`bid_status`~~ not offered: No bid operations exist in the Udbud.dk API (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml).
- ~~`list_messages`~~ not offered: No messaging endpoint: the API offers only notice validation, publication and retrieval (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml).
- ~~`send_message`~~ not offered: No messaging endpoint: the API offers only notice validation, publication and retrieval (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml).
- ~~`credits`~~ not offered: The API has no credits or quota endpoint (https://git.erst.dk/udbud-dk/sdk/-/blob/master/openapi.yml).

## Credentials

- `PLATFORM_MCP_UDBUD_DK_CLIENT_ID` — client_id issued by Udbud.dk / Erhvervsstyrelsen after registering your system (registration form linked from the SDK README) with the MU_API_DATASYNK role.
- `PLATFORM_MCP_UDBUD_DK_PRIVATE_KEY` — PEM RSA private key whose public key you expose in the JWKS endpoint registered with Udbud.dk (private_key_jwt client assertion, RS256).
- `PLATFORM_MCP_UDBUD_DK_KEY_ID` — kid of that key in your JWKS.

## Run

    uvx platform-mcp-hub serve udbud_dk          # Python
    npx -y platform-mcp-hub serve udbud_dk       # TypeScript
    claude mcp add udbud_dk -- uvx platform-mcp-hub serve udbud_dk

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/udbud_dk-mcp`. Python and TypeScript serve identical tools.

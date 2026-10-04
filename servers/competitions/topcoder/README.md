# Topcoder MCP server

Category: **competitions** · Docs: https://github.com/topcoder-platform/challenge-api-v6/blob/develop/docs/swagger.yaml · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/topcoder.json`; edit the catalog, not this file.

## Tools

- `discover` — `GET /v6/challenges` (https://github.com/topcoder-platform/challenge-api-v6/blob/develop/docs/swagger.yaml)
- `get_competition` — `GET /v6/challenges/{competition_id}` (https://github.com/topcoder-platform/challenge-api-v6/blob/develop/docs/swagger.yaml)
- `standings` — `GET /v6/challenges/{competition_id}` (https://github.com/topcoder-platform/challenge-api-v6/blob/develop/docs/swagger.yaml)
- ~~`me`~~ not offered: No credentials ('auth: none'); member endpoints need a Topcoder JWT from the Auth0 login, not an API key.
- ~~`my_entries`~~ not offered: Submissions live in the separate submission API behind a member JWT; the Challenge V6 swagger has no per-member listing.
- ~~`enter`~~ not offered: Registration is a resource creation in the separate Resources API behind a member JWT; not in the Challenge V6 swagger.
- ~~`submit`~~ not offered: Submissions are multipart file uploads to the separate submission API (member JWT); binary uploads are out of scope.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve competitions/topcoder          # Python
    npx -y platform-mcp-hub serve competitions/topcoder       # TypeScript
    claude mcp add topcoder -- uvx platform-mcp-hub serve competitions/topcoder

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/topcoder-competitions-mcp`. Python and TypeScript serve identical tools.

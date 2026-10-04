# Grand Challenge MCP server

Category: **competitions** · Docs: https://grand-challenge.org/api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/grand_challenge.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v1/profiles/users/self/` (https://grand-challenge.org/api/)
- `discover` — `GET /api/v1/challenges/` (https://grand-challenge.org/api/)
- `get_competition` — `GET /api/v1/challenges/{competition_id}/` (https://grand-challenge.org/api/)
- `standings` — `GET /api/v1/evaluations/` (https://grand-challenge.org/api/)
- ~~`my_entries`~~ not offered: The evaluations list has no creator filter (only submission__phase), so 'mine' cannot be selected; the submissions endpoints are not in the public schema.
- ~~`enter`~~ not offered: No join endpoint in the API schema; participation requests are made on the challenge site.
- ~~`submit`~~ not offered: Submissions are prediction files or algorithm container images uploaded on the challenge site; no submission endpoint in the API schema, and binary uploads are out of scope.

## Credentials

- `PLATFORM_MCP_GRAND_CHALLENGE_API_TOKEN` — Personal API token from https://grand-challenge.org/settings/api-tokens/ (sent as Authorization: Bearer).

## Run

    uvx platform-mcp-hub serve grand_challenge          # Python
    npx -y platform-mcp-hub serve grand_challenge       # TypeScript
    claude mcp add grand_challenge -- uvx platform-mcp-hub serve grand_challenge

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/grand_challenge-mcp`. Python and TypeScript serve identical tools.

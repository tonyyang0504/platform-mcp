# Freelancer MCP server

Category: **competitions** · Docs: https://developers.freelancer.com/docs/contests/contests · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/freelancer.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/0.1/self/` (https://developers.freelancer.com/docs/users/authenticated-users)
- `discover` — `GET /contests/0.1/contests/active/` (https://developers.freelancer.com/docs/contests/contests)
- `get_competition` — `GET /contests/0.1/contests/{competition_id}/` (https://developers.freelancer.com/docs/contests/contests)
- ~~`standings`~~ not offered: Contests have no ranking endpoint; the holder rates and awards entries (entry statuses won/eliminated only).
- ~~`my_entries`~~ not offered: GET /contests/0.1/entries/ (entrants[] filter) requires the advanced `fln:contest_manage` scope in addition to `basic`.
- ~~`enter`~~ not offered: No join step: a contest is entered by submitting an entry (see submit).
- ~~`submit`~~ not offered: POST /contests/0.1/entries/ submits an entry with its design files (multipart upload); binary uploads are out of scope.

## Credentials

- `PLATFORM_MCP_FREELANCER_ACCESS_TOKEN` — OAuth access token with the `basic` scope (a personal access token from https://accounts.freelancer.com/settings/develop works); sent in the freelancer-oauth-v1 header.

## Run

    uvx platform-mcp-hub serve competitions/freelancer          # Python
    npx -y platform-mcp-hub serve competitions/freelancer       # TypeScript
    claude mcp add freelancer -- uvx platform-mcp-hub serve competitions/freelancer

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/freelancer-competitions-mcp`. Python and TypeScript serve identical tools.

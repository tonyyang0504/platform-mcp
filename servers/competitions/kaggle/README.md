# Kaggle MCP server

Category: **competitions** · Docs: https://github.com/Kaggle/kaggle-api/blob/main/docs/competitions.md · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/kaggle.json`; edit the catalog, not this file.

## Tools

- `discover` — `POST /v1/competitions.CompetitionApiService/ListCompetitions` (https://github.com/Kaggle/kaggle-api/blob/main/docs/competitions.md#kaggle-competitions-list)
- `get_competition` — `POST /v1/competitions.CompetitionApiService/GetCompetition` (https://github.com/Kaggle/kaggle-api (kagglesdk competitions.CompetitionApiService))
- `standings` — `POST /v1/competitions.CompetitionApiService/GetLeaderboard` (https://github.com/Kaggle/kaggle-api/blob/main/docs/competitions.md#kaggle-competitions-leaderboard)
- `my_entries` — `POST /v1/competitions.CompetitionApiService/ListSubmissions` (https://github.com/Kaggle/kaggle-api/blob/main/docs/competitions.md#kaggle-competitions-submissions)
- ~~`me`~~ not offered: No account or whoami operation in the CLI docs or CompetitionApiService.
- ~~`enter`~~ not offered: No join operation: competition rules are accepted on the competition page at kaggle.com (the CLI docs have no join/accept command).
- ~~`submit`~~ not offered: CLI docs: `kaggle competitions submit <COMPETITION> -f <FILE_NAME> -m <MESSAGE>` — a file upload (StartSubmissionUpload, blob upload, then CreateSubmission); binary uploads are out of scope.

## Credentials

- `PLATFORM_MCP_KAGGLE_API_TOKEN` — Kaggle API token from https://www.kaggle.com/settings/api ('Generate New Token'; the value the CLI reads from KAGGLE_API_TOKEN / ~/.kaggle/access_token). Sent as Authorization: Bearer.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kaggle   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kaggle
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kaggle   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kaggle-mcp`. Python and TypeScript serve identical tools.

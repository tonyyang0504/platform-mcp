# Freelancehunt MCP server

Category: **deals** · Docs: https://apidocs.freelancehunt.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/freelancehunt.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /my/profile` (https://apidocs.freelancehunt.com/)
- `search_postings` — `GET /projects` (https://apidocs.freelancehunt.com/)
- `get_posting` — `GET /projects/{id}` (https://apidocs.freelancehunt.com/)
- `list_messages` — `GET /threads/{thread_id}` (https://apidocs.freelancehunt.com/)
- `send_message` — `POST /threads/{thread_id}` (https://apidocs.freelancehunt.com/)
- ~~`withdraw_bid`~~ not offered: Revoking needs both ids (POST /v2/projects/{project_id}/bids/{bid_id}/revoke); the vocabulary's withdraw_bid carries bid_id only.
- ~~`bid_status`~~ not offered: No per-bid endpoint: bids are listed with GET /v2/my/bids (filter[project_id], filter[status]) or per project, not fetched by bid id.
- ~~`credits`~~ not offered: No credit or balance endpoint in the API 2.0 collection.
- ~~`submit_bid`~~ not offered: POST /v2/projects/{project_id}/bids ('Add bid' in the Freelancehunt API 2.0 Postman collection) now answers 410 Gone: "This public endpoint is no longer available due to API v2 deprecation." (auth audit 2026-09-26, sent with a dummy token; the refusal comes before authentication).

## Credentials

- `PLATFORM_MCP_FREELANCEHUNT_TOKEN` — Personal API token from https://freelancehunt.com/my/api2, sent as 'Authorization: Bearer <token>'.
- `PLATFORM_MCP_FREELANCEHUNT_SAFE_TYPE` — Default payment protection for new bids: split, employer, developer or employer_cashless (Safe), per the 'Add bid' docs; leave unset for the platform default.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve freelancehunt   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve freelancehunt
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve freelancehunt   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/freelancehunt-mcp`. Python and TypeScript serve identical tools.

# Product Hunt MCP server

Category: **social** · Docs: https://api.producthunt.com/v2/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/producthunt.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /graphql` (https://github.com/producthunt/producthunt-api/blob/master/schema.graphql)
- `read_comments` — `POST /graphql` (https://github.com/producthunt/producthunt-api/blob/master/schema.graphql)
- `analytics_post` — `POST /graphql` (https://github.com/producthunt/producthunt-api/blob/master/schema.graphql)
- ~~`publish_text`~~ not offered: The API has no mutation that creates a post or launch; its mutations are goal* and userFollow* only (type Mutation in https://github.com/producthunt/producthunt-api/blob/master/schema.graphql), and 'partial write access' is granted case by case (https://api.producthunt.com/v2/docs).
- ~~`publish_image`~~ not offered: No post-creation or media-upload mutation exists (type Mutation in https://github.com/producthunt/producthunt-api/blob/master/schema.graphql).
- ~~`reply_comment`~~ not offered: No comment mutation exists (type Mutation in https://github.com/producthunt/producthunt-api/blob/master/schema.graphql: goalCheer, goalCreate, goalUpdate, userFollow ...).
- ~~`read_mentions`~~ not offered: The schema has no mentions or notifications query (type Query in https://github.com/producthunt/producthunt-api/blob/master/schema.graphql).
- ~~`delete`~~ not offered: No delete mutation for posts or comments exists (type Mutation in https://github.com/producthunt/producthunt-api/blob/master/schema.graphql).

## Credentials

- `PLATFORM_MCP_PRODUCTHUNT_TOKEN` — Product Hunt API token: the non-expiring developer_token of your application in the API dashboard (https://www.producthunt.com/v2/oauth/applications), or an OAuth user token with scopes public private; sent as 'Authorization: Bearer {token}' (https://api.producthunt.com/v2/docs).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve producthunt   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve producthunt
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve producthunt   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/producthunt-mcp`. Python and TypeScript serve identical tools.

# Supabase MCP server

Category: **builder_tools** · Docs: https://supabase.com/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/supabase.json`; edit the catalog, not this file.

## Tools

- `list_items` — `GET /{collection}` (https://supabase.com/docs/guides/api)
- `get_item` — `GET /{collection}` (https://docs.postgrest.org/en/v12/references/api/tables_views.html#horizontal-filtering)
- `create_item` — `POST /{collection}` (https://docs.postgrest.org/en/v12/references/api/tables_views.html#insertions)
- `update_item` — `POST /{collection}` (https://docs.postgrest.org/en/v12/references/api/tables_views.html#upsert)
- `delete_item` — `DELETE /{collection}` (https://docs.postgrest.org/en/v12/references/api/tables_views.html#deletions)
- ~~`me`~~ not offered: The Data API (PostgREST) has no identity endpoint for a secret key; the Management API (GET https://api.supabase.com/v1/projects/{ref}) needs a separate personal access token.
- ~~`generate_image`~~ not offered: Supabase has no generation endpoints.
- ~~`generate_video`~~ not offered: Supabase has no generation endpoints.
- ~~`get_job`~~ not offered: Supabase has no generation jobs.

## Credentials

- `PLATFORM_MCP_SUPABASE_SECRET_KEY` — Project secret key (sb_secret_…, Project Settings > API Keys), sent in the apikey header as Supabase documents for publishable/secret keys. It bypasses Row Level Security: keep it server-side.
- `PLATFORM_MCP_SUPABASE_PROJECT_REF` — Project reference (the subdomain of https://<ref>.supabase.co).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve supabase   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve supabase
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve supabase   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/supabase-mcp`. Python and TypeScript serve identical tools.

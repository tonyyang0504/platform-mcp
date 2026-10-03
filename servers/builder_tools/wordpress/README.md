# WordPress MCP server

Category: **builder_tools** · Docs: https://developer.wordpress.org/rest-api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/wordpress.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developer.wordpress.org/rest-api/reference/users/#retrieve-a-user-2)
- `list_items` — `GET /{collection}` (https://developer.wordpress.org/rest-api/reference/posts/#list-posts)
- `get_item` — `GET /{collection}/{item_id}` (https://developer.wordpress.org/rest-api/reference/posts/#retrieve-a-post)
- `create_item` — `POST /{collection}` (https://developer.wordpress.org/rest-api/reference/posts/#create-a-post)
- `update_item` — `POST /{collection}/{item_id}` (https://developer.wordpress.org/rest-api/reference/posts/#update-a-post)
- `delete_item` — `DELETE /{collection}/{item_id}` (https://developer.wordpress.org/rest-api/reference/posts/#delete-a-post)
- ~~`generate_image`~~ not offered: The WordPress REST API has no generation endpoints.
- ~~`generate_video`~~ not offered: The WordPress REST API has no generation endpoints.
- ~~`get_job`~~ not offered: No generation jobs in the WordPress REST API.

## Credentials

- `PLATFORM_MCP_WORDPRESS_USERNAME` — WordPress user login name.
- `PLATFORM_MCP_WORDPRESS_APPLICATION_PASSWORD` — Application Password for that user (Users > Profile > Application Passwords, WordPress 5.6+), sent with HTTP Basic auth over HTTPS.
- `PLATFORM_MCP_WORDPRESS_SITE` — The site's host (and path if WordPress lives in a subdirectory), e.g. example.com or example.com/blog; pretty permalinks must be enabled so /wp-json/ resolves.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve wordpress   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve wordpress
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve wordpress   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wordpress-mcp`. Python and TypeScript serve identical tools.

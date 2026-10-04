# Dev.to MCP server

Category: **social** · Docs: https://developers.forem.com/api/v1 · Verified: 2026-09-02

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/devto.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.forem.com/api/v1#operation/getUserMe)
- `read_comments` — `GET /comments` (https://developers.forem.com/api/v1#operation/getCommentsByArticleId)
- `analytics_post` — `GET /articles/{post_id}` (https://developers.forem.com/api/v1#operation/getArticleById)
- ~~`publish_text`~~ not offered: POST /api/articles takes a nested {article: {title, body_markdown, published, ...}} body and a mandatory title the vocabulary has no argument for; the runtime's body form is flat (arg name -> top-level key).
- ~~`publish_image`~~ not offered: Articles are markdown documents; images are `main_image`/inline markdown inside the same nested {article} body (see publish_text).
- ~~`reply_comment`~~ not offered: Forem API v1 has no create-comment endpoint; replies are written by humans on dev.to.
- ~~`read_mentions`~~ not offered: No mentions or notifications endpoint in Forem API v1.
- ~~`delete`~~ not offered: No delete endpoint in Forem API v1; PUT /api/articles/{id} can only unpublish.

## Credentials

- `PLATFORM_MCP_DEVTO_API_KEY` — DEV Community API key (dev.to > Settings > Extensions > DEV Community API Keys); sent as the `api-key` header.

## Run

    uvx platform-mcp-hub serve devto          # Python
    npx -y platform-mcp-hub serve devto       # TypeScript
    claude mcp add devto -- uvx platform-mcp-hub serve devto

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/devto-mcp`. Python and TypeScript serve identical tools.

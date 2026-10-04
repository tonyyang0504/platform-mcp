# Facebook MCP server

Category: **social** · Docs: https://developers.facebook.com/docs/pages-api/posts · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/facebook.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{page_id}` (https://developers.facebook.com/docs/graph-api/reference/page/)
- `publish_text` — `POST /{page_id}/feed` (https://developers.facebook.com/docs/pages-api/posts)
- `publish_image` — `POST /{page_id}/photos` (https://developers.facebook.com/docs/pages-api/posts)
- `read_comments` — `GET /{post_id}/comments` (https://developers.facebook.com/docs/graph-api/reference/object/comments)
- `reply_comment` — `POST /{comment_id}/comments` (https://developers.facebook.com/docs/pages-api/comments-mentions)
- `read_mentions` — `GET /{page_id}/tagged` (https://developers.facebook.com/docs/graph-api/reference/page/tagged/)
- `delete` — `DELETE /{post_id}` (https://developers.facebook.com/docs/pages-api/posts)
- `analytics_post` — `GET /{post_id}` (https://developers.facebook.com/docs/graph-api/reference/post/)

## Credentials

- `PLATFORM_MCP_FACEBOOK_PAGE_ACCESS_TOKEN` — Page access token of the Facebook Page (Facebook Login for Business: a person who can perform the CREATE_CONTENT, MANAGE and MODERATE tasks on the Page grants pages_manage_posts, pages_manage_engagement, pages_read_engagement, pages_read_user_engagement and, for read_mentions, pages_read_user_content + pages_show_list; exchange for a long-lived token, then GET /me/accounts for the Page token). 'you will need to implement Facebook Login to ask for the following permissions and receive a Page access token' (https://developers.facebook.com/docs/pages-api/posts); sent as `Authorization: Bearer`.
- `PLATFORM_MCP_FACEBOOK_PAGE_ID` — Numeric id of the Facebook Page that posts (the Page the token belongs to); publish_text, publish_image, read_mentions and me call /<page_id>/... Env: PLATFORM_MCP_FACEBOOK_PAGE_ID.

## Run

    uvx platform-mcp-hub serve facebook          # Python
    npx -y platform-mcp-hub serve facebook       # TypeScript
    claude mcp add facebook -- uvx platform-mcp-hub serve facebook

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/facebook-mcp`. Python and TypeScript serve identical tools.

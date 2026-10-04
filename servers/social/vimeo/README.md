# Vimeo MCP server

Category: **social** · Docs: https://developer.vimeo.com/api/upload/videos · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/vimeo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developer.vimeo.com/api/reference/users)
- `read_comments` — `GET /videos/{post_id}/comments` (https://developer.vimeo.com/api/reference/videos#get_comments)
- `delete` — `DELETE /videos/{post_id}` (https://developer.vimeo.com/api/reference/videos#delete_video)
- `analytics_post` — `GET /videos/{post_id}` (https://developer.vimeo.com/api/reference/videos#get_video)
- ~~`publish_text`~~ not offered: Vimeo has no text posts; the closest call, POST /videos/{video_id}/comments ('Add a comment to a video', https://developer.vimeo.com/api/reference/videos#create_comment), is a comment on a video, not a post.
- ~~`publish_image`~~ not offered: Vimeo hosts videos only; there is no image post (https://developer.vimeo.com/api/reference/videos).
- ~~`reply_comment`~~ not offered: POST /videos/{video_id}/comments/{comment_id}/replies needs the video id as well as the comment id (https://developer.vimeo.com/api/reference/videos#create_comment_reply); the reply input carries only comment_id.
- ~~`read_mentions`~~ not offered: The API has no mentions or notifications endpoint for a user (https://developer.vimeo.com/api/reference/users).

## Credentials

- `PLATFORM_MCP_VIMEO_ACCESS_TOKEN` — Vimeo personal access token (developer.vimeo.com > My Apps > your app > Generate an access token, authenticated, scopes public private edit delete interact stats) or an OAuth authorization-code token; Vimeo access tokens do not expire unless revoked. Sent as 'Authorization: bearer <token>'.

## Run

    uvx platform-mcp-hub serve vimeo          # Python
    npx -y platform-mcp-hub serve vimeo       # TypeScript
    claude mcp add vimeo -- uvx platform-mcp-hub serve vimeo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/vimeo-mcp`. Python and TypeScript serve identical tools.

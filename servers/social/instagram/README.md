# Instagram MCP server

Category: **social** · Docs: https://developers.facebook.com/docs/instagram-platform/comment-moderation · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/instagram.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{ig_user_id}` (https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user)
- `read_comments` — `GET /{post_id}/comments` (https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/comments)
- `reply_comment` — `POST /{comment_id}/replies` (https://developers.facebook.com/docs/instagram-platform/comment-moderation)
- `read_mentions` — `GET /{ig_user_id}/tags` (https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/tags)
- `analytics_post` — `GET /{post_id}` (https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media)
- ~~`publish_text`~~ not offered: Instagram has no text-only post: 'In order to publish a media object, it must have a container' created with image_url or video_url (https://developers.facebook.com/docs/instagram-platform/content-publishing).
- ~~`publish_image`~~ not offered: Two calls: 'send a POST request to the /<IG_ID>/media endpoint' with image_url to create a container, then 'Send a POST request to the /<IG_ID>/media_publish endpoint with ... creation_id set to the container ID' (https://developers.facebook.com/docs/instagram-platform/content-publishing); the runtime makes one call per tool.
- ~~`delete`~~ not offered: The IG Media reference documents reading only; DELETE is documented for IG Comments (DELETE /<IG_COMMENT_ID>, https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-comment), not for published media.

## Credentials

- `PLATFORM_MCP_INSTAGRAM_ACCESS_TOKEN` — Instagram API with Facebook Login (host graph.facebook.com): a User or Page access token from Facebook Login for Business for a person with a role on the Facebook Page linked to the Instagram professional (Business or Creator) account, with instagram_basic, instagram_manage_comments, pages_read_engagement (and pages_show_list); sent as `Authorization: Bearer` (https://developers.facebook.com/docs/instagram-platform/comment-moderation).
- `PLATFORM_MCP_INSTAGRAM_IG_USER_ID` — Instagram professional account id (IG User id, e.g. 17841405822304914) - GET /{page_id}?fields=instagram_business_account returns it. me and read_mentions call /<ig_user_id>. Env: PLATFORM_MCP_INSTAGRAM_IG_USER_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve instagram   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve instagram
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve instagram   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/instagram-mcp`. Python and TypeScript serve identical tools.

# TikTok MCP server

Category: **social** · Docs: https://developers.tiktok.com/docs/en/content-posting-api-get-started · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/tiktok.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/user/info/` (https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info)
- `publish_image` — `POST /v2/post/publish/content/init/` (https://developers.tiktok.com/doc/content-posting-api-reference-photo-post)
- `analytics_post` — `POST /v2/video/query/` (https://developers.tiktok.com/doc/tiktok-api-v2-video-query)
- ~~`publish_text`~~ not offered: The Content Posting API posts only video or photo content ('media_type ... Currently only PHOTO is allowed' for /v2/post/publish/content/init/, https://developers.tiktok.com/doc/content-posting-api-reference-photo-post); there is no text-only post.
- ~~`read_comments`~~ not offered: Comment data is not in the Display API video object (fields: id, create_time, cover_image_url, share_url, video_description, duration, …, like_count, comment_count, share_count, view_count; https://developers.tiktok.com/doc/tiktok-api-v2-video-query); comment lists are only in the separately approved Research API.
- ~~`reply_comment`~~ not offered: No comment-reply endpoint exists in the Login Kit / Display / Content Posting APIs (https://developers.tiktok.com/doc/tiktok-api-v2-video-query lists only counts).
- ~~`read_mentions`~~ not offered: No mentions endpoint exists in the Display or Content Posting APIs (https://developers.tiktok.com/docs/en/content-posting-api-get-started).
- ~~`delete`~~ not offered: The Content Posting API has no delete call (https://developers.tiktok.com/docs/en/content-posting-api-get-started: init, upload, status fetch only); posts are deleted in the TikTok app.

## Credentials

- `PLATFORM_MCP_TIKTOK_CLIENT_KEY` — Client key of your TikTok for Developers app (https://developers.tiktok.com/apps).
- `PLATFORM_MCP_TIKTOK_CLIENT_SECRET` — Client secret of the same app.
- `PLATFORM_MCP_TIKTOK_REFRESH_TOKEN` — The creator's refresh_token from the Login Kit authorization-code exchange (POST /v2/oauth/token/, valid 365 days) with scopes user.info.basic, video.publish, video.list. Access tokens (24 h) are minted from it; a rotated refresh_token replaces it (persisted when PLATFORM_MCP_STATE_DIR is set).
- `PLATFORM_MCP_TIKTOK_PRIVACY_LEVEL` — privacy_level for direct photo posts: one of the creator's privacy_level_options from /v2/post/publish/creator_info/query/ (PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY). Unaudited apps can only use SELF_ONLY.

## Run

    uvx platform-mcp-hub serve social/tiktok          # Python
    npx -y platform-mcp-hub serve social/tiktok       # TypeScript
    claude mcp add tiktok -- uvx platform-mcp-hub serve social/tiktok

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tiktok-social-mcp`. Python and TypeScript serve identical tools.

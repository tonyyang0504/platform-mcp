# Weibo MCP server

Category: **social** · Docs: https://open.weibo.com/wiki/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/weibo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /account/get_uid.json` (https://open.weibo.com/wiki/2/account/get_uid)
- `publish_text` — `POST /statuses/share.json` (https://open.weibo.com/wiki/2/statuses/share)
- `read_comments` — `GET /comments/show.json` (https://open.weibo.com/wiki/2/comments/show)
- `read_mentions` — `GET /statuses/mentions.json` (https://open.weibo.com/wiki/2/statuses/mentions)
- `delete` — `POST /statuses/destroy.json` (https://open.weibo.com/wiki/2/statuses/destroy)
- `analytics_post` — `GET /statuses/count.json` (https://open.weibo.com/wiki/2/statuses/count)
- ~~`publish_image`~~ not offered: Pictures must be uploaded as the binary pic part of a multipart/form-data statuses/share request ('上传图片时...需要采用multipart/form-data编码方式', https://open.weibo.com/wiki/2/statuses/share); the runtime has no multipart upload and URLs are not accepted.
- ~~`reply_comment`~~ not offered: comments/reply needs both cid (the comment) and id (the Weibo post) (https://open.weibo.com/wiki/2/comments/reply); the reply input carries only comment_id.

## Credentials

- `PLATFORM_MCP_WEIBO_ACCESS_TOKEN` — Weibo OAuth2 access_token, sent as the access_token parameter ('采用OAuth授权方式为必填参数'). For your own account use the developer authorization of your app (开发者授权, valid 5 years); ordinary user authorizations last 1 or 30 days depending on the app's level and cannot be refreshed server-side (refresh tokens exist only for the official mobile SDK) (https://open.weibo.com/wiki/%E6%8E%88%E6%9D%83%E6%9C%BA%E5%88%B6%E8%AF%B4%E6%98%8E).
- `PLATFORM_MCP_WEIBO_USER_IP` — Real public IP of the operating user, sent as rip on statuses/share ('开发者上报的操作用户真实IP，形如：211.156.0.1').

## Run

    uvx platform-mcp-hub serve weibo          # Python
    npx -y platform-mcp-hub serve weibo       # TypeScript
    claude mcp add weibo -- uvx platform-mcp-hub serve weibo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/weibo-mcp`. Python and TypeScript serve identical tools.

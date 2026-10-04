# WeChat MCP server

Category: **social** · Docs: https://developers.weixin.qq.com/doc/service/guide/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/wechat.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /get_api_domain_ip` (https://developers.weixin.qq.com/doc/service/api/base/api_getapidomainip)
- `publish_text` — `POST /message/mass/sendall` (https://developers.weixin.qq.com/doc/service/api/notify/message/api_sendall)
- `read_comments` — `POST /comment/list` (https://developers.weixin.qq.com/doc/service/api/leaving/api_listcomment)
- `delete` — `POST /message/mass/delete` (https://developers.weixin.qq.com/doc/service/api/notify/message/api_deletemassmsg)
- ~~`publish_image`~~ not offered: Mass-sent images must be WeChat media_ids (images.media_ids) obtained by uploading the file first (https://developers.weixin.qq.com/doc/service/api/notify/message/api_sendall, 新增临时素材); the runtime has no multipart upload, and image URLs are not accepted.
- ~~`reply_comment`~~ not offered: replyComment needs msg_data_id and index of the article besides user_comment_id (https://developers.weixin.qq.com/doc/service/api/leaving/api_replycomment); a comment id alone cannot address it.
- ~~`read_mentions`~~ not offered: Official Accounts have no mention concept; user messages are pushed to the account's callback URL only (https://developers.weixin.qq.com/doc/service/guide/).
- ~~`analytics_post`~~ not offered: Article statistics (datacube getarticlesummary / getarticletotal) are queried by begin_date / end_date for the whole account, not by a post id (https://developers.weixin.qq.com/doc/service/api/).

## Credentials

- `PLATFORM_MCP_WECHAT_APPID` — AppID of the Official Account (服务号 / 公众号), sent with the AppSecret to GET https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential (https://developers.weixin.qq.com/doc/service/api/base/api_getaccesstoken); the calling server's IP must be on the account's API IP whitelist (errcode 40164 otherwise).
- `PLATFORM_MCP_WECHAT_SECRET` — AppSecret of the Official Account. The returned access_token (7200 s) travels as the access_token query parameter of every call; fetching a new one invalidates tokens held by other servers of the same account.

## Run

    uvx platform-mcp-hub serve wechat          # Python
    npx -y platform-mcp-hub serve wechat       # TypeScript
    claude mcp add wechat -- uvx platform-mcp-hub serve wechat

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wechat-mcp`. Python and TypeScript serve identical tools.

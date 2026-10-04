# Baijiahao MCP server

Category: **social** · Docs: https://baijiahao.baidu.com/docs/#/normalcomplex/developer/serviceIntroduction · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/baijiahao.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /builderinner/open/resource/query/articleListall` (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/getArticleLists)
- `read_comments` — `POST /builderinner/open/resource/query/articleCommentList` (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/getSingleArtsComment)
- `delete` — `POST /builderinner/open/resource/article/withdraw` (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/withdrawalContent)
- `analytics_post` — `POST /builderinner/open/resource/query/articleStatistics` (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/getArtsRealTimeData)
- ~~`publish_text`~~ not offered: article/publish (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/publishPT) requires a title of 5-40 characters and a unique origin_url ('相同URL的文章会被认为是同一篇文章，禁止提交') besides the rich-text content; the vocabulary's publish_text carries only text, so neither required field can be supplied.
- ~~`publish_image`~~ not offered: There is no image post: 发布图片 (image/pushPic, https://baijiahao.baidu.com/docs/#/normalcomplex/developer/pushPic) submits images with per-image id, title, objurl, fromurl and edit_time to Baidu 图片搜索 (Image Search) for institutional original authors, not to the account's feed; image posts otherwise go through article/publish, which needs a title and origin_url.
- ~~`reply_comment`~~ not offered: No comment-reply call is documented: the 评论管理 group has only read calls (commentAuthorListall, articleCommentStatistics, articleCommentList, articleCommentReplyList; https://baijiahao.baidu.com/docs/#/normalcomplex/developer/getAuthorCommentList).
- ~~`read_mentions`~~ not offered: No mention or @-notification call is documented in the developer docs (https://baijiahao.baidu.com/docs/#/normalcomplex/developer/serviceIntroduction lists 内容发布, 内容管理, 文章查询, 评论管理, 数据查询, 用户管理).

## Credentials

- `PLATFORM_MCP_BAIJIAHAO_APP_ID` — 作者帐号ID (app_id) shown when you enable 开发者 service in the 百家号 creator console (开通开发者服务，获取app_token及app_id).
- `PLATFORM_MCP_BAIJIAHAO_APP_TOKEN` — 授权密钥 (app_token) from the same 开发者 settings; sent in the request body of every call. Reset it at once if it leaks.

## Run

    uvx platform-mcp-hub serve baijiahao          # Python
    npx -y platform-mcp-hub serve baijiahao       # TypeScript
    claude mcp add baijiahao -- uvx platform-mcp-hub serve baijiahao

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/baijiahao-mcp`. Python and TypeScript serve identical tools.

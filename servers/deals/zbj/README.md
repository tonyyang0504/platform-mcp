# Zhubajie MCP server

Category: **deals** · Docs: https://open.zbj.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/zbj.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=6&groupId=3)
- `get_posting` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=93&groupId=12)
- ~~`search_postings`~~ not offered: The 需求API group has a single method, zbj.task.getDetailById ('通过需求ID查询需求详情', https://open.zbj.com/api/apiIndex); there is no call that searches or lists open demands.
- ~~`submit_bid`~~ not offered: No bid/proposal call is documented: the 交易API methods cover work already joined (queryParticipatedPieceWorks, bidWork = '提交悬赏/众包稿件' manuscript upload, contracts, acceptance), not quoting an amount on a demand (https://open.zbj.com/api/apiIndex).
- ~~`withdraw_bid`~~ not offered: zbj.trade.sellerGiveUp ('服务商投标后放弃需求', https://open.zbj.com/api/apiDetailIndex?methodId=95&groupId=4) takes openid + taskId + a required optionId from zbj.trade.giveUpReasonOps; there is no bid id and the vocabulary has no reason option.
- ~~`bid_status`~~ not offered: No bid ids are issued; outcomes are split across zbj.trade.getSigningOutcome / getWorkInfo per trade type (https://open.zbj.com/api/apiIndex).
- ~~`list_messages`~~ not offered: The IM group only has zbj.msg.getLastInstant ('获取最近即时消息信息', https://open.zbj.com/api/apiIndex); there is no thread message list.
- ~~`send_message`~~ not offered: No message-sending method is documented in the IM group (https://open.zbj.com/api/apiIndex).
- ~~`credits`~~ not offered: No balance or bid-credit method is documented (https://open.zbj.com/api/apiIndex).

## Credentials

- `PLATFORM_MCP_ZBJ_APP_KEY` — appKey (应用证书) of your approved ZOP application (open.zbj.com > 控制台).
- `PLATFORM_MCP_ZBJ_APP_SECRET` — Application secret (应用密钥); signs every call as uppercase hex SHA1 of secret + sorted name/value pairs + secret. Never sent on the wire.
- `PLATFORM_MCP_ZBJ_ACCESS_TOKEN` — accessToken (访问令牌) from the ZOP OAuth2.0 authorisation of your 猪八戒 account.
- `PLATFORM_MCP_ZBJ_OPENID` — Your 猪八戒 openid (the user identifier returned by the ZOP OAuth2.0 authorisation), used by zbj.user.getUserBaseInfo.

## Run

    uvx platform-mcp-hub serve zbj          # Python
    npx -y platform-mcp-hub serve zbj       # TypeScript
    claude mcp add zbj -- uvx platform-mcp-hub serve zbj

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zbj-mcp`. Python and TypeScript serve identical tools.

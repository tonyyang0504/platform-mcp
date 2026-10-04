# KakaoTalk MCP server

Category: **messaging** · Docs: https://developers.kakao.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/kakao.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/user/me` (https://developers.kakao.com/docs/en/kakaologin/rest-api)
- `send` — `POST /v1/api/talk/friends/message/default/send` (https://developers.kakao.com/docs/en/kakaotalk-message/rest-api#default-template-msg-friend)
- ~~`list_inbound`~~ not offered: The Kakao Talk Message API only sends ('Send to me' / 'Send to friends', https://developers.kakao.com/docs/en/kakaotalk-message/rest-api); there is no endpoint to read received messages.
- ~~`get_thread`~~ not offered: No conversation or history endpoint exists in the Kakao Talk Message API (https://developers.kakao.com/docs/en/kakaotalk-message/rest-api).
- ~~`reply`~~ not offered: Messages have no thread ids to reply to; use send to the friend's uuid (https://developers.kakao.com/docs/en/kakaotalk-message/rest-api).
- ~~`mark_read`~~ not offered: The Kakao Talk Message API has no read-state endpoint (https://developers.kakao.com/docs/en/kakaotalk-message/rest-api).

## Credentials

- `PLATFORM_MCP_KAKAO_CLIENT_ID` — REST API key of the Kakao app ([App] > [Platform Key] > [REST API key]), sent as client_id to POST https://kauth.kakao.com/oauth/token (https://developers.kakao.com/docs/en/kakaologin/rest-api).
- `PLATFORM_MCP_KAKAO_CLIENT_SECRET` — Client secret of the REST API key; 'Required when the setting is [ON]' (enabled by default for new keys).
- `PLATFORM_MCP_KAKAO_REFRESH_TOKEN` — Refresh token from Kakao Login (authorization code flow) of the SENDING user, with consent to the talk_message scope and friends-list access (friends scope); valid about 60 days (refresh_token_expires_in 5184000). Kakao returns a renewed refresh_token when less than a month is left: the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/kakao.json (mode 0600).
- `PLATFORM_MCP_KAKAO_LINK_URL` — Web URL opened when the message is tapped (text template link.web_url / mobile_web_url, 'O' required); its domain must be registered as a Web domain under Product Link on the app management page (https://developers.kakao.com/docs/en/message-template/default).

## Run

    uvx platform-mcp-hub serve kakao          # Python
    npx -y platform-mcp-hub serve kakao       # TypeScript
    claude mcp add kakao -- uvx platform-mcp-hub serve kakao

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kakao-mcp`. Python and TypeScript serve identical tools.

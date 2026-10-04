# Reddit MCP server

Category: **social** · Docs: https://www.reddit.com/dev/api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/reddit.json`; edit the catalog, not this file.

## Tools

- `read_comments` — `GET /comments/{post_id}` (https://www.reddit.com/dev/api/#GET_comments_{article})
- `analytics_post` — `GET /api/info` (https://www.reddit.com/dev/api/#GET_api_info)
- ~~`me`~~ not offered: GET /api/v1/me (scope identity) 'returns the identity of the user'; an application-only client_credentials token is issued to a client 'not acting on behalf of' a user (https://github.com/reddit-archive/reddit/wiki/OAuth2), so there is no account to describe.
- ~~`publish_text`~~ not offered: POST /api/submit (scope submit) posts as a user; it needs a user-context token from the authorization-code flow, which the runtime cannot obtain (app-only tokens have no user).
- ~~`publish_image`~~ not offered: POST /api/media/asset.json upload lease + POST /api/submit kind=image needs a user-context token and a file upload; neither is available to the runtime.
- ~~`reply_comment`~~ not offered: POST /api/comment (scope submit) needs a user-context token from the authorization-code flow; the app-only token cannot comment.
- ~~`read_mentions`~~ not offered: GET /message/inbox|unread and /message/mentions (scope privatemessages) read a user's inbox and need a user-context token; the app-only token has no inbox.
- ~~`delete`~~ not offered: POST /api/del (scope edit) deletes the user's own thing and needs a user-context token; the app-only token owns nothing.

## Credentials

- `PLATFORM_MCP_REDDIT_CLIENT_ID` — Client id of a `script` or `web` app registered at https://www.reddit.com/prefs/apps; sent as the HTTP Basic username to POST https://www.reddit.com/api/v1/access_token (grant_type=client_credentials).
- `PLATFORM_MCP_REDDIT_CLIENT_SECRET` — The app's secret (HTTP Basic password on the token request). The resulting app-only bearer expires after `expires_in` seconds and is re-requested automatically; it carries no user context, so only read endpoints are offered.
- `PLATFORM_MCP_REDDIT_USER_AGENT` — Reddit requires a unique, descriptive User-Agent of the form "<platform>:<app ID>:<version string> (by /u/<reddit username>)", e.g. "server:com.example.myapp:v1.0 (by /u/you)"; default or misrepresented agents are throttled or blocked (https://github.com/reddit-archive/reddit/wiki/API). The runtime appends it to its own platform-mcp/reddit token.

## Run

    uvx platform-mcp-hub serve social/reddit          # Python
    npx -y platform-mcp-hub serve social/reddit       # TypeScript
    claude mcp add reddit -- uvx platform-mcp-hub serve social/reddit

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/reddit-social-mcp`. Python and TypeScript serve identical tools.

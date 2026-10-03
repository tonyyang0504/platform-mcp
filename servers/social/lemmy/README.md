# Lemmy MCP server

Category: **social** · Docs: https://github.com/LemmyNet/lemmy-js-client · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/lemmy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://{instance}/api/v3/site` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/GetSiteResponse.ts)
- `read_comments` — `GET https://{instance}/api/v3/comment/list` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/GetComments.ts)
- `read_mentions` — `GET https://{instance}/api/v3/user/mention` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/GetPersonMentions.ts)
- `analytics_post` — `GET https://{instance}/api/v3/post` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/PostAggregates.ts)
- `publish_text` — `POST https://{instance}/api/v3/post` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/CreatePost.ts)
- `publish_image` — `POST https://{instance}/api/v3/post` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/CreatePost.ts)
- `delete` — `POST https://{instance}/api/v3/post/delete` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/DeletePost.ts)
- ~~`reply_comment`~~ not offered: POST /api/v3/comment needs CreateComment {content, post_id: PostId (required), parent_id?: CommentId} (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/CreateComment.ts): a reply must name the POST it belongs to, the vocabulary passes only the comment's id, and the runtime cannot look the post up first (GET /api/v3/comment?id= would be a second call), so the request cannot be composed.

## Credentials

- `PLATFORM_MCP_LEMMY_USERNAME_OR_EMAIL` — Username or e-mail of the account on its instance; sent as `username_or_email` to POST https://<instance>/api/v3/user/login (Login {username_or_email, password, totp_2fa_token?}, https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/Login.ts).
- `PLATFORM_MCP_LEMMY_PASSWORD` — The account's password. The runtime exchanges it for the LoginResponse `jwt` (https://raw.githubusercontent.com/LemmyNet/lemmy-js-client/0.19.4/src/types/LoginResponse.ts) and sends 'Authorization: Bearer <jwt>' (lemmy-js-client setHeaders pattern); the token is cached for a day and re-issued on expiry or 401. Accounts with TOTP enabled cannot log in this way (totp_2fa_token is not sent). Mark automated accounts as bot_account in the profile settings.
- `PLATFORM_MCP_LEMMY_INSTANCE` — Host of the account's Lemmy instance without scheme, e.g. lemmy.ml; every call (including the login) goes to https://<instance>/api/v3/... (the v3 API served by the 0.19.x release line that public instances run; Lemmy 1.0's /api/v4 is not covered).
- `PLATFORM_MCP_LEMMY_COMMUNITY_ID` — Numeric id of the community the account posts to (CreatePost.community_id, an integer: shown by GET https://<instance>/api/v3/community?name=<name> as community_view.community.id); sent as a JSON integer on publish_text / publish_image. Env PLATFORM_MCP_LEMMY_COMMUNITY_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve lemmy   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve lemmy
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve lemmy   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lemmy-mcp`. Python and TypeScript serve identical tools.

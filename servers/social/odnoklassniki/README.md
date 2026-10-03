# Odnoklassniki MCP server

Category: **social** · Docs: https://apiok.ru/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/odnoklassniki.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /fb.do` (https://apiok.ru/dev/methods/rest/users/users.getCurrentUser)
- `publish_text` — `POST /fb.do` (https://apiok.ru/dev/methods/rest/mediatopic/mediatopic.post)
- `read_comments` — `POST /fb.do` (https://apiok.ru/dev/methods/rest/discussions/discussions.getComments)
- `delete` — `POST /fb.do` (https://apiok.ru/dev/methods/rest/mediatopic/mediatopic.deleteTopic)
- `analytics_post` — `POST /fb.do` (https://apiok.ru/dev/methods/rest/group/group.getStatTopic)
- ~~`publish_image`~~ not offered: mediatopic.post photo media take 'id - параметр token, передаваемый в метод photosV2.commit во время загрузки фотографий на сервер' (https://apiok.ru/dev/methods/rest/mediatopic/mediatopic.post): images must first be uploaded as multipart files to the URL from photosV2.getUploadUrl; there is no image-by-URL media type.
- ~~`reply_comment`~~ not offered: Replying needs the discussion (topic) id and type besides the comment id; the documented comment method page https://apiok.ru/dev/methods/rest/discussions/discussions.addDiscussionComment returns 404 (checked 2026-09-25), so no documented reply call with only comment_id exists.
- ~~`read_mentions`~~ not offered: The OK REST method list (https://apiok.ru/dev/methods/) has no mentions feed for a group or user.

## Credentials

- `PLATFORM_MCP_ODNOKLASSNIKI_APPLICATION_KEY` — Public key of your OK application (application_key, from the app registration e-mail / app settings at https://ok.ru/app/setup).
- `PLATFORM_MCP_ODNOKLASSNIKI_APPLICATION_SECRET_KEY` — Secret key of the same application (application_secret_key). Only used to compute sig; never sent.
- `PLATFORM_MCP_ODNOKLASSNIKI_ACCESS_TOKEN` — User access_token with VALUABLE_ACCESS and GROUP_CONTENT, from the OAuth flow (https://apiok.ru/ext/oauth/) or the app's permanent 'Вечный access_token' in the app settings. Sent in the POST body, excluded from sig as the convention requires.
- `PLATFORM_MCP_ODNOKLASSNIKI_GROUP_ID` — Numeric id (gid) of the OK group you administer; posts, comments and statistics are for this group's topics (needs the GROUP_CONTENT permission).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve odnoklassniki   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve odnoklassniki
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve odnoklassniki   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/odnoklassniki-mcp`. Python and TypeScript serve identical tools.

# Farcaster MCP server

Category: **social** · Docs: https://docs.neynar.com/reference/publish-cast · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/farcaster.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/farcaster/user/bulk/` (https://docs.neynar.com/reference/fetch-bulk-users)
- `publish_text` — `POST /v2/farcaster/cast/` (https://docs.neynar.com/reference/publish-cast)
- `read_comments` — `GET /v2/farcaster/cast/conversation/` (https://docs.neynar.com/reference/lookup-cast-conversation)
- `reply_comment` — `POST /v2/farcaster/cast/` (https://docs.neynar.com/reference/publish-cast)
- `read_mentions` — `GET /v2/farcaster/notifications/` (https://docs.neynar.com/reference/fetch-all-notifications)
- `delete` — `DELETE /v2/farcaster/cast/` (https://docs.neynar.com/reference/delete-cast)
- `analytics_post` — `GET /v2/farcaster/cast/` (https://docs.neynar.com/reference/lookup-cast-by-hash-or-url)
- `publish_image` — `POST /v2/farcaster/cast/` (https://docs.neynar.com/reference/publish-cast)

## Credentials

- `PLATFORM_MCP_FARCASTER_API_KEY` — Neynar API key from https://dev.neynar.com: 'All API endpoints require an API key. Include the following header with every request: x-api-key' (https://docs.neynar.com/reference). Writes additionally need a signer (config field signer_uuid) created and approved for the same API key.
- `PLATFORM_MCP_FARCASTER_SIGNER_UUID` — UUID of an approved signer for the publishing account ('signer_uuid is paired with API key, can't use a uuid made with a different API key'; 'In order to post a cast signer_uuid must be approved', https://docs.neynar.com/reference/publish-cast). Required for publish_text, reply_comment and delete; env PLATFORM_MCP_FARCASTER_SIGNER_UUID.
- `PLATFORM_MCP_FARCASTER_FID` — Farcaster id (integer) of the connected account, used by `me` (GET /v2/farcaster/user/bulk/?fids=) and read_mentions (GET /v2/farcaster/notifications/?fid=); env PLATFORM_MCP_FARCASTER_FID.

## Run

    uvx platform-mcp-hub serve farcaster          # Python
    npx -y platform-mcp-hub serve farcaster       # TypeScript
    claude mcp add farcaster -- uvx platform-mcp-hub serve farcaster

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/farcaster-mcp`. Python and TypeScript serve identical tools.

# Kling AI MCP server

Category: **builder_tools** · Docs: https://kling.ai/document-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/kling.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /account/costs` (https://kling.ai/document-api/api/assets/account-usage)
- `generate_image` — `POST /v1/images/generations` (https://kling.ai/document-api/api/image/3-0-omni)
- `generate_video` — `POST /text-to-video/{model}` (https://kling.ai/document-api/api/video/3-0-omni)
- `get_job` — `GET /tasks` (https://kling.ai/document-api/api/video/3-0-omni)
- ~~`list_items`~~ not offered: No content-item resource; task listings (POST /tasks by cursor) are generation history, not items.
- ~~`get_item`~~ not offered: No content-item resource.
- ~~`create_item`~~ not offered: No content-item resource.
- ~~`update_item`~~ not offered: No content-item resource.
- ~~`delete_item`~~ not offered: No content-item resource.

## Credentials

- `PLATFORM_MCP_KLING_API_KEY` — Kling AI API key (kling.ai/dev console > '+ Create a new API Key'; shown once), sent as Authorization: Bearer. The legacy AccessKey/SecretKey JWT scheme is not needed.

## Run

    uvx platform-mcp-hub serve kling          # Python
    npx -y platform-mcp-hub serve kling       # TypeScript
    claude mcp add kling -- uvx platform-mcp-hub serve kling

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kling-mcp`. Python and TypeScript serve identical tools.

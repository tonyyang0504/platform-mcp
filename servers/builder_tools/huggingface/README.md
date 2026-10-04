# Hugging Face MCP server

Category: **builder_tools** · Docs: https://huggingface.co/docs/hub/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/huggingface.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/whoami-v2` (https://huggingface.co/.well-known/openapi.md)
- `list_items` — `GET /api/{collection}` (https://huggingface.co/docs/hub/api)
- `get_item` — `GET /api/{collection}/{item_id}` (https://huggingface.co/docs/huggingface_hub/package_reference/hf_api)
- `create_item` — `POST /api/repos/create` (https://huggingface.co/.well-known/openapi.md)
- `update_item` — `PUT /api/{collection}/{item_id}/settings` (https://huggingface.co/.well-known/openapi.md)
- ~~`generate_image`~~ not offered: Hub inference (router.huggingface.co / hf-inference text-to-image) answers with image bytes, which a JSON tool result cannot carry; no URL/job variant is documented.
- ~~`generate_video`~~ not offered: Hub inference text-to-video answers with video bytes; no URL/job variant is documented.
- ~~`get_job`~~ not offered: No generation job resource on the Hub API (Jobs run compute, not generations).
- ~~`delete_item`~~ not offered: DELETE /api/repos/delete takes the repo as separate `name` and `organization` body fields (huggingface_hub HfApi.delete_repo), while item_id is the combined namespace/repo id; the runtime cannot split one argument into two fields.

## Credentials

- `PLATFORM_MCP_HUGGINGFACE_TOKEN` — Hugging Face user access token (https://huggingface.co/settings/tokens); a write (or fine-grained repo write) token for create/update.

## Run

    uvx platform-mcp-hub serve huggingface          # Python
    npx -y platform-mcp-hub serve huggingface       # TypeScript
    claude mcp add huggingface -- uvx platform-mcp-hub serve huggingface

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/huggingface-mcp`. Python and TypeScript serve identical tools.

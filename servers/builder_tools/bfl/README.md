# Black Forest Labs (FLUX) MCP server

Category: **builder_tools** · Docs: https://docs.bfl.ai · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/bfl.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /credits` (https://docs.bfl.ai/api-reference/utility/get-the-users-credits)
- `generate_image` — `POST /{model}` (https://docs.bfl.ai/api-reference/models/edit-or-create-an-image-with-flux1-kontext-pro)
- `generate_video` — `POST /flux-3-video` (https://docs.bfl.ai/api-reference/utility/generate-a-video-with-flux-3)
- ~~`get_job`~~ not offered: Results must be polled at the per-task `polling_url`: 'When using the primary global endpoint (api.bfl.ai) or regional endpoints (api.eu.bfl.ai, api.us.bfl.ai), you must use the polling_url returned in the initial request response' (https://docs.bfl.ai/api_integration/integration_guidelines). That URL's host is a per-task cluster, and the runtime does not send credentials to a host taken from a response or an argument (needs a response-URL follow with a host allow-list); use the webhook_url config field instead.
- ~~`list_items`~~ not offered: No content-item resource; the only listings are fine-tunes (GET /v1/my_finetunes, ids only).
- ~~`get_item`~~ not offered: No content-item resource.
- ~~`create_item`~~ not offered: No content-item resource.
- ~~`update_item`~~ not offered: No content-item resource.
- ~~`delete_item`~~ not offered: No content-item resource (POST /v1/delete_finetune deletes a fine-tune, which this vocabulary does not model).

## Credentials

- `PLATFORM_MCP_BFL_API_KEY` — BFL API key (bfl.ai dashboard > organisation > project > API keys), sent as the x-key header. Requests spend pay-as-you-go credits (1 credit = $0.01).
- `PLATFORM_MCP_BFL_WEBHOOK_URL` — Optional HTTPS URL that BFL POSTs finished results to (webhook_url on every generation request); the way to receive results, since polling needs the per-task polling_url.

## Run

    uvx platform-mcp-hub serve bfl          # Python
    npx -y platform-mcp-hub serve bfl       # TypeScript
    claude mcp add bfl -- uvx platform-mcp-hub serve bfl

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bfl-mcp`. Python and TypeScript serve identical tools.

# Ideogram MCP server

Category: **builder_tools** · Docs: https://developer.ideogram.ai · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/ideogram.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /models` (https://developer.ideogram.ai/api-reference/custom-model-training/list-models)
- `generate_image` — `POST /generate` (https://developer.ideogram.ai/api-reference/legacy-endpoints/generate)
- `get_job` — `GET /v1/generations/{job_id}` (https://developer.ideogram.ai/api-reference/generate-images/get-generation)
- `list_items` — `GET /models` (https://developer.ideogram.ai/api-reference/custom-model-training/list-models)
- `get_item` — `GET /models/{item_id}` (https://developer.ideogram.ai/api-reference/custom-model-training/get-model)
- ~~`generate_video`~~ not offered: The only video endpoint (POST /v1/product-360-video, 'Create a looping 360-degree product video') takes a multipart/form-data product image upload; multipart request bodies are not supported by the runtime.
- ~~`create_item`~~ not offered: Datasets and models are created with multipart asset uploads / training requests (https://developer.ideogram.ai/api-reference/custom-model-training/upload-dataset-assets), not a JSON item body the vocabulary can express.
- ~~`update_item`~~ not offered: No update endpoint for models or datasets is documented.
- ~~`delete_item`~~ not offered: No delete endpoint for models or datasets is documented.

## Credentials

- `PLATFORM_MCP_IDEOGRAM_API_KEY` — Ideogram API key (developer.ideogram.ai > API dashboard, after adding a payment method and credits), sent as the Api-Key header.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ideogram   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ideogram
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ideogram   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ideogram-mcp`. Python and TypeScript serve identical tools.

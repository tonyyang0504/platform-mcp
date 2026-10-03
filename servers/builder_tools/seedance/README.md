# Seedance (BytePlus ModelArk) MCP server

Category: **builder_tools** · Docs: https://docs.byteplus.com/en/docs/ModelArk/1520757 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/seedance.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /contents/generations/tasks` (https://docs.byteplus.com/en/docs/ModelArk/1521675)
- `generate_image` — `POST /images/generations` (https://docs.byteplus.com/en/docs/ModelArk/1541523)
- `generate_video` — `POST /contents/generations/tasks` (https://docs.byteplus.com/en/docs/ModelArk/1520757)
- `get_job` — `GET /contents/generations/tasks/{job_id}` (https://docs.byteplus.com/en/docs/ModelArk/1521309)
- ~~`list_items`~~ not offered: No content-item resource; the task list (GET /contents/generations/tasks) is generation history.
- ~~`get_item`~~ not offered: No content-item resource.
- ~~`create_item`~~ not offered: No content-item resource.
- ~~`update_item`~~ not offered: No content-item resource.
- ~~`delete_item`~~ not offered: No content-item resource (DELETE /contents/generations/tasks/{id} cancels or deletes a generation task).

## Credentials

- `PLATFORM_MCP_SEEDANCE_API_KEY` — BytePlus ModelArk API key (console.byteplus.com > ModelArk > API keys, ap-southeast-1), sent as Authorization: Bearer. Activate the Seedance/Seedream models first.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve seedance   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve seedance
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve seedance   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/seedance-mcp`. Python and TypeScript serve identical tools.

# ElevenLabs MCP server

Category: **builder_tools** · Docs: https://elevenlabs.io/docs/api-reference · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/builder_tools/elevenlabs.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/user` (https://elevenlabs.io/docs/api-reference/user/get)
- `list_items` — `GET /v2/voices` (https://elevenlabs.io/docs/api-reference/voices/search)
- `get_item` — `GET /v1/voices/{item_id}` (https://elevenlabs.io/docs/api-reference/voices/get)
- `delete_item` — `DELETE /v1/voices/{item_id}` (https://elevenlabs.io/docs/api-reference/voices/delete)
- ~~`generate_image`~~ not offered: ElevenLabs is an audio platform; it has no image generation endpoint.
- ~~`generate_video`~~ not offered: No video generation endpoint (dubbing POST /v1/dubbing takes a multipart file or source_url and returns audio/video bytes per language).
- ~~`get_job`~~ not offered: Speech, sound-effect and music generation are synchronous and answer with audio bytes ('Returns audio file', https://elevenlabs.io/docs/api-reference/text-to-speech/convert), which a JSON tool result cannot carry; there is no job/URL variant for them.
- ~~`create_item`~~ not offered: Voices are created with multipart uploads of audio samples (POST /v1/voices/add, 'multipart/form-data', https://elevenlabs.io/docs/api-reference/voices/ivc/create); multipart request bodies are not supported by the runtime.
- ~~`update_item`~~ not offered: POST /v1/voices/{voice_id}/edit is multipart/form-data ('This endpoint expects a multipart form with multiple files', https://elevenlabs.io/docs/api-reference/voices/edit); multipart request bodies are not supported by the runtime.

## Credentials

- `PLATFORM_MCP_ELEVENLABS_API_KEY` — ElevenLabs API key (Profile > API Keys; scoped keys need voices read/write for these tools), sent as the xi-api-key header.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve elevenlabs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve elevenlabs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve elevenlabs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/elevenlabs-mcp`. Python and TypeScript serve identical tools.

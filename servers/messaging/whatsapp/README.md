# WhatsApp Business MCP server

Category: **messaging** · Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/whatsapp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{phone_number_id}` (https://developers.facebook.com/docs/whatsapp/cloud-api/reference/phone-numbers)
- `send` — `POST /{phone_number_id}/messages` (https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages)
- `mark_read` — `POST /{phone_number_id}/messages` (https://developers.facebook.com/docs/whatsapp/cloud-api/guides/mark-message-as-read)
- ~~`list_inbound`~~ not offered: Incoming messages arrive only through the messages webhook ('When you receive a message webhook indicating an incoming message', https://developers.facebook.com/docs/whatsapp/cloud-api/guides/mark-message-as-read); the Cloud API has no message-history read endpoint.
- ~~`get_thread`~~ not offered: No conversation-history endpoint exists; message content is delivered only by webhooks (https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks).
- ~~`reply`~~ not offered: A reply is a send to the user's phone number with an optional context.message_id; the Messages API needs `to` ('WhatsApp user phone number', https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages), which the reply verb does not carry. Use send.

## Credentials

- `PLATFORM_MCP_WHATSAPP_ACCESS_TOKEN` — System user access token or business token of the WhatsApp Business Account (whatsapp_business_messaging, whatsapp_business_management), sent as `Authorization: Bearer` as in every Cloud API example (https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages).
- `PLATFORM_MCP_WHATSAPP_PHONE_NUMBER_ID` — WhatsApp business phone number ID (not the phone number itself, e.g. 106540352242922; GET /<WABA_ID>/phone_numbers lists them). Every call goes to /<phone_number_id>/... Env: PLATFORM_MCP_WHATSAPP_PHONE_NUMBER_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve whatsapp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve whatsapp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve whatsapp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/whatsapp-mcp`. Python and TypeScript serve identical tools.

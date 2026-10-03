# Matrix MCP server

Category: **messaging** · Docs: https://spec.matrix.org/latest/client-server-api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/matrix.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://{homeserver}/_matrix/client/v3/account/whoami` (https://spec.matrix.org/latest/client-server-api/#get_matrixclientv3accountwhoami)
- `send` — `PUT https://{homeserver}/_matrix/client/v3/rooms/{to}/send/m.room.message/{txnId}` (https://spec.matrix.org/latest/client-server-api/#put_matrixclientv3roomsroomidsendeventtypetxnid)
- `reply` — `PUT https://{homeserver}/_matrix/client/v3/rooms/{channel}/send/m.room.message/{txnId}` (https://spec.matrix.org/latest/client-server-api/#threading)
- `list_inbound` — `GET https://{homeserver}/_matrix/client/v3/rooms/{channel}/messages` (https://spec.matrix.org/latest/client-server-api/#get_matrixclientv3roomsroomidmessages)
- `get_thread` — `GET https://{homeserver}/_matrix/client/v1/rooms/{channel}/relations/{thread_id}/m.thread` (https://spec.matrix.org/latest/client-server-api/#get_matrixclientv1roomsroomidrelationseventidreltype)
- `mark_read` — `POST https://{homeserver}/_matrix/client/v3/rooms/{channel}/receipt/m.read/{message_id}` (https://spec.matrix.org/latest/client-server-api/#post_matrixclientv3roomsroomidreceiptreceipttypeeventid)

## Credentials

- `PLATFORM_MCP_MATRIX_ACCESS_TOKEN` — Access token of the account (from a login flow or the client's settings), sent as 'Authorization: Bearer' — 'Access tokens may be provided via a request header, using the Authentication Bearer scheme: Authorization: Bearer TheTokenHere' (https://spec.matrix.org/latest/client-server-api/#using-access-tokens).
- `PLATFORM_MCP_MATRIX_HOMESERVER` — Host of the account's homeserver client API without scheme (e.g. matrix.org, or the m.homeserver base_url from /.well-known/matrix/client without https://); every call goes to https://<homeserver>/_matrix/client/... Env: PLATFORM_MCP_MATRIX_HOMESERVER.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve matrix   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve matrix
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve matrix   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/matrix-mcp`. Python and TypeScript serve identical tools.

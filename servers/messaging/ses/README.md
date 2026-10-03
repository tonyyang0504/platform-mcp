# Amazon SES MCP server

Category: **messaging** · Docs: https://docs.aws.amazon.com/ses/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/ses.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/email/account` (https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_GetAccount.html)
- `send` — `POST /v2/email/outbound-emails` (https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_SendEmail.html)
- ~~`list_inbound`~~ not offered: SES v2 has no API to read received mail: receiving is configured as receipt rules that deliver to S3, SNS or Lambda (https://docs.aws.amazon.com/ses/latest/dg/receiving-email.html); the API reference (https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_Operations.html) has no mailbox read operation.
- ~~`get_thread`~~ not offered: SES is a send-only service with no conversation or thread store (https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_Operations.html).
- ~~`reply`~~ not offered: Replies need the original message's Message-ID/References headers, which SES does not store (no inbound read API, https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_Operations.html); use send with the reply address.
- ~~`mark_read`~~ not offered: SES keeps no read state for messages (https://docs.aws.amazon.com/ses/latest/APIReference-V2/API_Operations.html).

## Credentials

- `PLATFORM_MCP_SES_ACCESS_KEY_ID` — AWS access key id of an IAM principal allowed ses:SendEmail and ses:GetAccount.
- `PLATFORM_MCP_SES_SECRET_ACCESS_KEY` — The matching AWS secret access key; used only to derive the SigV4 signing key.
- `PLATFORM_MCP_SES_SESSION_TOKEN` — Session token when the keys are temporary STS credentials (sent as X-Amz-Security-Token).
- `PLATFORM_MCP_SES_REGION` — AWS Region of your SES account, e.g. us-east-1, eu-west-1 (the endpoint is email.<region>.amazonaws.com).
- `PLATFORM_MCP_SES_FROM_ADDRESS` — Verified sender identity (address or an address on a verified domain) used as FromEmailAddress.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ses   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ses
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ses   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ses-mcp`. Python and TypeScript serve identical tools.

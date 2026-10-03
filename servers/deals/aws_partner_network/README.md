# AWS Partner Network MCP server

Category: **deals** · Docs: https://docs.aws.amazon.com/partner-central/latest/APIReference/Welcome.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/aws_partner_network.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /` (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_ListEngagementInvitations.html)
- `search_postings` — `POST /` (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_ListEngagementInvitations.html)
- `get_posting` — `POST /` (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_GetEngagementInvitation.html)
- `submit_bid` — `POST /` (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_StartEngagementByAcceptingInvitationTask.html)
- `bid_status` — `POST /` (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_ListEngagementByAcceptingInvitationTasks.html)
- ~~`withdraw_bid`~~ not offered: An accepted invitation cannot be withdrawn: RejectEngagementInvitation applies only to invitations not yet accepted ('If the partner decides not to pursue the opportunity, they can reject the invitation … Once rejected, access to the opportunity is lost', https://docs.aws.amazon.com/partner-central/latest/developer-guide/working-with-opportunities-from-aws.html), and it takes the invitation id, not the acceptance task id that submit_bid returns.
- ~~`list_messages`~~ not offered: The Selling API has no messaging operations; its actions cover opportunities, engagement invitations, engagements, resource snapshots and solutions (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_Operations.html).
- ~~`send_message`~~ not offered: The Selling API has no messaging operations (https://docs.aws.amazon.com/partner-central/latest/APIReference/API_Operations.html); an invitation carries a one-way InvitationMessage from AWS.
- ~~`credits`~~ not offered: Referrals are free to accept; the Selling API has no credit, quota-balance or connects concept (https://docs.aws.amazon.com/partner-central/latest/APIReference/Welcome.html).

## Credentials

- `PLATFORM_MCP_AWS_PARTNER_NETWORK_ACCESS_KEY_ID` — Access key id of an IAM user or role session in the AWS Marketplace seller account linked to Partner Central, with a policy such as AWSPartnerCentralOpportunityManagement (https://docs.aws.amazon.com/partner-central/latest/developer-guide/setup-authentication.html).
- `PLATFORM_MCP_AWS_PARTNER_NETWORK_SECRET_ACCESS_KEY` — Secret access key of that IAM identity; never sent, used for the SigV4 signature.
- `PLATFORM_MCP_AWS_PARTNER_NETWORK_SESSION_TOKEN` — Session token when the keys are temporary (assumed role / SSO); sent as X-Amz-Security-Token.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve aws_partner_network   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve aws_partner_network
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve aws_partner_network   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/aws_partner_network-mcp`. Python and TypeScript serve identical tools.

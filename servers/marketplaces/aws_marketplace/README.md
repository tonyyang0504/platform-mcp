# AWS Marketplace MCP server

Category: **marketplaces** · Docs: https://docs.aws.amazon.com/marketplace-catalog/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/aws_marketplace.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /ListEntities` (https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_ListEntities.html)
- `list_products` — `POST /ListEntities` (https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_ListEntities.html)
- `get_product` — `GET /DescribeEntity` (https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_DescribeEntity.html)
- `list_sales` — `POST https://agreement-marketplace.us-east-1.amazonaws.com/` (https://docs.aws.amazon.com/marketplace/latest/APIReference/API_marketplace-agreements_SearchAgreements.html)
- `list_refunds` — `POST https://agreement-marketplace.us-east-1.amazonaws.com/` (https://docs.aws.amazon.com/marketplace/latest/APIReference/API_marketplace-agreements_ListBillingAdjustmentRequests.html)
- ~~`create_product`~~ not offered: Products are created through StartChangeSet with a CreateProduct change whose DetailsDocument is entity-type specific (https://docs.aws.amazon.com/marketplace-catalog/latest/api-reference/API_StartChangeSet.html), and prices belong to a separate Offer entity (UpdatePricingTerms); a name + price + currency cannot form a valid change set.
- ~~`update_price`~~ not offered: Prices are pricing terms on an Offer (UpdatePricingTerms change with per-dimension RateCards; https://docs.aws.amazon.com/marketplace/latest/APIReference/work-with-private-offers.html), not a single price on a product.
- ~~`get_sales_stats`~~ not offered: Revenue figures come from the seller reports / delivery data feeds delivered to S3 (https://docs.aws.amazon.com/marketplace/latest/userguide/reports-and-data-feed.html), not from a synchronous API.
- ~~`refund`~~ not offered: BatchCreateBillingAdjustmentRequest requires originalInvoiceId, currencyCode, adjustmentReasonCode and clientToken for each entry besides agreementId and amount (https://docs.aws.amazon.com/marketplace/latest/APIReference/API_marketplace-agreements_BatchCreateBillingAdjustmentRequest.html); the vocabulary's refund (sale_id, amount, reason) has no invoice id, so a valid request cannot be built.

## Credentials

- `PLATFORM_MCP_AWS_MARKETPLACE_ACCESS_KEY_ID` — AWS access key id of the seller account's IAM principal with aws-marketplace:ListEntities, DescribeEntity and SearchAgreements (e.g. the AWSMarketplaceSellerProductsReadOnly policy plus agreement read access).
- `PLATFORM_MCP_AWS_MARKETPLACE_SECRET_ACCESS_KEY` — The matching AWS secret access key; only used to derive the SigV4 signing key.
- `PLATFORM_MCP_AWS_MARKETPLACE_SESSION_TOKEN` — Session token when the keys are temporary STS credentials.
- `PLATFORM_MCP_AWS_MARKETPLACE_ENTITY_TYPE` — Catalog entity type of your listings: SaaSProduct, AmiProduct, ContainerProduct, DataProduct (or Offer).

## Run

    uvx platform-mcp-hub serve aws_marketplace          # Python
    npx -y platform-mcp-hub serve aws_marketplace       # TypeScript
    claude mcp add aws_marketplace -- uvx platform-mcp-hub serve aws_marketplace

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/aws_marketplace-mcp`. Python and TypeScript serve identical tools.

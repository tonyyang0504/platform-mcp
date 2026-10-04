# Companies House MCP server

Category: **sales** · Docs: https://developer.company-information.service.gov.uk/ · Verified: 2026-09-05

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/sales/uk_companies_house.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /search/companies` (https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/search-companies)
- `search` — `GET /search/companies` (https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/search-companies)
- `get_company` — `GET /company/{id}` (https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/company-profile/company-profile)

## Credentials

- `PLATFORM_MCP_UK_COMPANIES_HOUSE_API_KEY` — Companies House Public Data API key (free, from https://developer.company-information.service.gov.uk/). Sent as the HTTP Basic user name with an empty password: 'the Companies House API takes the username as the API key and ignores the password' (https://developer-specs.company-information.service.gov.uk/guides/authorisation).

## Run

    uvx platform-mcp-hub serve uk_companies_house          # Python
    npx -y platform-mcp-hub serve uk_companies_house       # TypeScript
    claude mcp add uk_companies_house -- uvx platform-mcp-hub serve uk_companies_house

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/uk_companies_house-mcp`. Python and TypeScript serve identical tools.

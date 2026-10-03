# SEC EDGAR company search MCP server

Category: **sales** · Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/sales/us_sec_edgar.json`; edit the catalog, not this file.

## Tools

- `get_company` — `GET /submissions/CIK{id}.json` (https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- ~~`me`~~ not offered: EDGAR is anonymous — there are no credentials and no account endpoint; only the User-Agent contact is declared (https://www.sec.gov/os/accessing-edgar-data).
- ~~`search`~~ not offered: The documented JSON APIs are keyed by the 10-digit CIK and none accepts a company-name query; no name-search endpoint is documented on https://www.sec.gov/search-filings/edgar-application-programming-interfaces (the static company_tickers.json list would need client-side filtering the adapter cannot express).

## Credentials

- `PLATFORM_MCP_US_SEC_EDGAR_CONTACT` — Company name and e-mail, required by SEC fair-access rules: 'Sample Company Name AdminContact@<sample company domain>.com' is appended to the User-Agent (https://www.sec.gov/os/accessing-edgar-data). Env: PLATFORM_MCP_US_SEC_EDGAR_CONTACT.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve us_sec_edgar   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve us_sec_edgar
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve us_sec_edgar   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/us_sec_edgar-mcp`. Python and TypeScript serve identical tools.

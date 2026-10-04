# Homerun MCP server

Category: **jobs** · Docs: https://developers.homerun.co/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/homerun.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /vacancies` (https://developers.homerun.co/#tag/Vacancies/operation/vacancies.get)
- `search` — `GET /vacancies?filter[status]=public&include[]=location&include[]=department&include[]=salaryIndication` (https://developers.homerun.co/#tag/Vacancies/operation/vacancies.get)
- `get_posting` — `GET /vacancies/{id}?include[]=location&include[]=department&include[]=salaryIndication&include[]=page_content` (https://developers.homerun.co/#tag/Vacancies/operation/vacancies.vacancy-id.get)
- ~~`apply`~~ not offered: POST /job-applications creates an applicant as the employer (key scope job-applications:write, 'sourced' flag), i.e. the company's own ATS import, not a candidate applying; candidates apply through the Homerun career page.
- ~~`list_messages`~~ not offered: The API has no message or conversation endpoints (only notes, tags, answers, files and the confirmation email).

## Credentials

- `PLATFORM_MCP_HOMERUN_API_KEY` — Homerun Public API v2 key generated on https://app.homerun.co/settings/integrations with the `vacancies:read` scope; sent as `Authorization: Bearer`.

## Run

    uvx platform-mcp-hub serve homerun          # Python
    npx -y platform-mcp-hub serve homerun       # TypeScript
    claude mcp add homerun -- uvx platform-mcp-hub serve homerun

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/homerun-mcp`. Python and TypeScript serve identical tools.

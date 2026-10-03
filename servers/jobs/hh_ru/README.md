# hh.ru MCP server

Category: **jobs** · Docs: https://api.hh.ru/openapi/redoc · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/hh_ru.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://api.hh.ru/openapi/redoc#tag/Informaciya-o-prilozhenii/operation/get-current-user-info)
- `search` — `GET /vacancies` (https://api.hh.ru/openapi/redoc#tag/Poisk-vakansij/operation/get-vacancies)
- `get_posting` — `GET /vacancies/{id}` (https://api.hh.ru/openapi/redoc#tag/Vakansii/operation/get-vacancy)
- ~~`apply`~~ not offered: Applying (POST /negotiations) needs an applicant's user token from the authorization-code flow plus a resume_id; this server authenticates as the application (client credentials), which cannot act for a job seeker.
- ~~`list_messages`~~ not offered: Negotiation messages belong to an applicant or employer user token (authorization-code flow); the application token used here has no user.

## Credentials

- `PLATFORM_MCP_HH_RU_CLIENT_ID` — client_id of an application registered at https://dev.hh.ru/admin; used to obtain an application token (grant_type=client_credentials at https://api.hh.ru/token).
- `PLATFORM_MCP_HH_RU_CLIENT_SECRET` — client_secret of the same hh.ru application.
- `PLATFORM_MCP_HH_RU_USER_AGENT` — Your application name and developer contact e-mail, e.g. 'MyApp/1.0 (me@example.com)'. hh.ru requires a User-Agent (or HH-User-Agent) naming the application and the developer's contact address ('Указание в заголовке названия приложения и контактной почты разработчика'); it is appended to the server's User-Agent.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hh_ru   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hh_ru
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hh_ru   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hh_ru-mcp`. Python and TypeScript serve identical tools.

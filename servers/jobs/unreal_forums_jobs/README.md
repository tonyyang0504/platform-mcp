# Unreal Engine forums: Job Offerings MCP server

Category: **jobs** · Docs: https://forums.unrealengine.com/c/community/got-skills-looking-for-talent/job-offerings/76.rss · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/unreal_forums_jobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /search.json` (https://docs.discourse.org/#tag/Search/operation/search)
- `get_posting` — `GET /t/{id}.json` (https://docs.discourse.org/#tag/Topics/operation/getTopic)
- ~~`me`~~ not offered: Public, keyless reads; there is no account to verify without a Discourse user API key.
- ~~`apply`~~ not offered: The job offers are forum topics; candidates reply or contact the poster by forum message or the e-mail given in the post — there is no application endpoint.
- ~~`list_messages`~~ not offered: Reading private messages needs a Discourse user API key for a forums.unrealengine.com account (Epic account sign-in), which this keyless adapter does not use.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/unreal_forums_jobs          # Python
    npx -y platform-mcp-hub serve jobs/unreal_forums_jobs       # TypeScript
    claude mcp add unreal_forums_jobs -- uvx platform-mcp-hub serve jobs/unreal_forums_jobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/unreal_forums_jobs-jobs-mcp`. Python and TypeScript serve identical tools.

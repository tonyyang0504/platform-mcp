# EvalAI MCP server

Category: **competitions** · Docs: https://eval.ai/api/docs/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/evalai.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/auth/user/` (https://eval.ai/api/docs/)
- `discover` — `GET /api/challenges/challenge/present/approved/public` (https://eval.ai/api/docs/)
- `get_competition` — `GET /api/challenges/challenge/{competition_id}/` (https://eval.ai/api/docs/)
- `standings` — `GET /api/jobs/challenge_phase_split/{competition_id}/leaderboard/` (https://eval.ai/api/docs/)
- `enter` — `POST /api/challenges/challenge/{competition_id}/participant_team/{participant_team_pk}` (https://eval.ai/api/docs/)
- ~~`my_entries`~~ not offered: Participant submissions are listed per phase (GET /api/jobs/challenge/{challenge_id}/challenge_phase/{challenge_phase_id}/submission/); the vocabulary has no phase id, and /api/jobs/challenge/{challenge_pk}/submission/ is host-only.
- ~~`submit`~~ not offered: POST /api/jobs/challenge/{challenge_id}/challenge_phase/{challenge_phase_id}/submission/ takes a multipart `input_file` (or a presigned-URL upload); binary uploads are out of scope.

## Credentials

- `PLATFORM_MCP_EVALAI_AUTH_TOKEN` — EvalAI auth token from https://eval.ai/web/profile ('Get your Auth Token'; the token the evalai CLI uses). Sent as Authorization: Bearer.
- `PLATFORM_MCP_EVALAI_PARTICIPANT_TEAM_ID` — Numeric id of your EvalAI participant team (from GET /api/participants/participant_team or the Participant Teams page); needed only by `enter`.

## Run

    uvx platform-mcp-hub serve evalai          # Python
    npx -y platform-mcp-hub serve evalai       # TypeScript
    claude mcp add evalai -- uvx platform-mcp-hub serve evalai

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/evalai-mcp`. Python and TypeScript serve identical tools.

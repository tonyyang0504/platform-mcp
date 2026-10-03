# platform-mcp: notes for coding agents

Read `README.md`, `CONTRIBUTING.md` and `docs/ADAPTER_CONTRACT.md` first. Edit the catalog, not generated files.

## Gate commands (safe to run; CI runs the same)

```bash
.venv/bin/python -m platform_mcp_hub lint [catalog/<category>/<id>.json]
.venv/bin/python -m platform_mcp_hub try <id> <verb> '<json args>'     # one live read call (no write tools)
.venv/bin/python -m platform_mcp_hub smoke <id>                        # both runtimes over stdio, no network
.venv/bin/python -m platform_mcp_hub verify --only <category>/<id> --lang both --auth any   # live, read tools only
.venv/bin/python tools/gen_all.py && git diff --exit-code -- servers catalog runtime/python/README.md
.venv/bin/python -m pytest -q tests
node --test tests/*.test.mjs
git status / git diff
```

Personal permission allowlists for these belong in `.claude/settings.local.json` (git-ignored), not in a committed
settings file.

## Rules

- Evidence only: every endpoint cites the vendor's docs and a `verified_at` date; never guess field names.
- A runtime change lands in `runtime/python` and `runtime/typescript` together, with the same test in both languages.
- Never call write tools against a live platform; never commit credentials or recorded responses that contain them.
- Commits are signed off (`git commit -s`, DCO).

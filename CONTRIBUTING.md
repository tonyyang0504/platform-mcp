# Contributing to platform-mcp

Thank you for helping. Useful contributions, roughly in order of value:

- a **new platform** (a catalog entry with an `adapter` block) or a fix to an existing entry;
- a **status record** for a platform that cannot be served yet (gated docs, partner-only access, official vendor MCP);
- runtime work that keeps the Python and TypeScript runtimes identical;
- reports of an endpoint that changed (open an issue with the docs URL).

## Ground rules

- Edit the **catalog**, not generated files. `servers/`, `catalog/index.json`, `catalog/directory.json` and
  `runtime/python/README.md` are rewritten by `python tools/gen_all.py`; CI fails when they are stale.
- **Evidence only.** Every endpoint cites the platform's own documentation (`docs` URL) and carries a `verified_at` date
  on which you opened that page. Write `UNCONFIRMED` rather than guess. The full contract is
  [`docs/ADAPTER_CONTRACT.md`](docs/ADAPTER_CONTRACT.md).
- Tool names are the category's verb vocabulary (`catalog/schema/vocab.json`) only.
- Never commit secrets, real account data or recorded fixtures that contain them. Live tests are opt-in.
- Both runtimes must pass: a runtime change lands in `runtime/python` **and** `runtime/typescript` in the same pull
  request, with the same test in `tests/test_*_python.py` and `tests/*.typescript.test.mjs`.

## Development setup

```bash
git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp
uv venv -p 3.12 && uv pip install -e ".[dev]"                      # Python 3.10+ works; CI uses 3.12
(cd runtime/typescript && npm ci --ignore-scripts && npm run build)  # Node 20+
```

## The gates (run them before you push; CI runs the same)

```bash
.venv/bin/python -m platform_mcp_hub lint                 # catalog lint: 0 errors
.venv/bin/python tools/gen_all.py && git diff --exit-code -- servers catalog runtime/python/README.md
.venv/bin/python -m pytest -q tests                        # Python: runtime, contract, security, CLI tests
node --test tests/*.test.mjs                               # TypeScript: the same contract + CLI parity with Python
```

For a single entry: `platform-mcp-hub lint catalog/<category>/<id>.json`, `platform-mcp-hub smoke <id>` (both
runtimes over stdio, no network) and `platform-mcp-hub try <id> <verb> '<json args>'` (one real read call: the request,
the raw response and the mapped result).

## Adding a platform

1. `platform-mcp-hub describe <a similar id>` and an entry of the same category are good templates.
2. Write `catalog/<category>/<id>.json` with `"version": "0.1.0"`, `docs_url`, `verified_at` and an `adapter` block
   ([`docs/ADAPTER_CONTRACT.md`](docs/ADAPTER_CONTRACT.md)); every unmapped verb goes under `not_offered` with the
   documented reason.
3. `platform-mcp-hub lint catalog/<category>/<id>.json`, then `python tools/gen_all.py`.
4. Contract tests: `tests/test_<id>_python.py` (respx) and `tests/<id>.typescript.test.mjs` (a fake fetch), shaped
   exactly like the documented responses: the tool list, one mapping per tool with the request asserted, one error.
5. Live check (keyless or with your own credentials, read tools only):
   `platform-mcp-hub verify --only <category>/<id> --lang both --auth any`. Add realistic arguments to `PLANS` in
   `runtime/python/platform_mcp_hub/live_verify.py` when the defaults do not fit, and record the result with
   `--record` once both runtimes are `working`.

## Pull requests

- Keep a pull request to one platform or one runtime change; describe the evidence (docs URLs you opened).
- Fill in the pull request template; CI must be green.
- Add a line to `CHANGELOG.md` under "Unreleased" for anything user-visible.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying the [Developer Certificate of Origin 1.1](https://developercertificate.org/):
you wrote the change or have the right to submit it under the project's licence (Apache-2.0). Sign off with
`git commit -s`, which adds a line such as:

```
Signed-off-by: Jane Developer <jane@example.com>
```

Use your real name (or a consistent pseudonym you are known by) and an address you can be reached at; a GitHub
`noreply` address is fine. Forgot? `git commit --amend -s` (one commit) or `git rebase --signoff main` (several).

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Security issues go through
[`SECURITY.md`](SECURITY.md), never a public issue.

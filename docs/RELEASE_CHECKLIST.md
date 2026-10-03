# Release checklist

`platform-mcp-hub` is published from GitHub Actions (`.github/workflows/release.yml`) when a tag `vX.Y.Z` is pushed:
PyPI through **trusted publishing** (OIDC, no stored token) and npm with **provenance** (OIDC trusted publishing).
Until the first release, `catalog/schema/release.json` stays `"published": false`, and every README, `describe` and the
directory server say "unpublished — run from source" (security review SR-17).

## One-time setup (operator)

1. **GitHub environments.** In the repository settings → Environments, create `pypi` and `npm`. Add yourself as a
   required reviewer on both (a release then waits for your approval) and restrict them to tags `v*`.
2. **PyPI trusted publisher** (the project does not exist yet, so use a *pending* publisher): pypi.org → Your account →
   Publishing → Add a new pending publisher → GitHub:
   - PyPI project name: `platform-mcp-hub`
   - Owner: `tonyyang0504` · Repository: `platform-mcp`
   - Workflow name: `release.yml` · Environment: `pypi`
3. **npm trusted publisher.** npm requires the package to exist before a trusted publisher can be attached, so the very
   first npm release is manual, then OIDC takes over:
   - From a clean checkout of the tag: `cd runtime/typescript && npm ci --ignore-scripts && npm run build && npm publish --access public`
     (npm 11.5+; `prepack` copies the catalog into the package; log in with 2FA).
   - npmjs.com → `platform-mcp-hub` → Settings → Trusted publishing → GitHub Actions: organisation/user
     `tonyyang0504`, repository `platform-mcp`, workflow `release.yml`, environment `npm`.
   - Then, in the package settings, set "Require two-factor authentication and disallow tokens" so only the workflow
     (and you, with 2FA) can publish.
   - If you prefer to wait, leave npm for later: the workflow's npm job fails without the trusted publisher while PyPI
     still publishes.
4. **MCP registry** (optional, after both registries have 0.1.0): the registry verifies a PyPI package by the
   `mcp-name: <server name>` lines in its README (`runtime/python/README.md` lists all of them) and an npm package by
   `mcpName` in package.json (`io.github.tonyyang0504/platform-mcp-hub`, the directory). Publishing the 456
   `servers/*/server.json` files is a separate decision (`mcp-publisher login github` then `mcp-publisher publish` per
   directory); the workflow does not do it.

## Release

1. All gates green on `main` (CI): lint, `tools/gen_all.py` without a diff, Python and TypeScript tests, parity,
   installed-package smoke, CodeQL, secret scan.
2. Set the version in three places (CI checks they agree): `runtime/python/platform_mcp_hub/__init__.py`
   (`__version__`), `runtime/typescript/package.json` and `runtime/typescript/src/version.ts`; `pyproject.toml`'s
   `version`. Move "Unreleased" in `CHANGELOG.md` under the version.
3. First release only: set `"published": true` in `catalog/schema/release.json`, run `python tools/gen_all.py`, commit
   the regenerated READMEs and directory snapshot. This switches every run hint from "from source" to `uvx`/`npx`.
4. Tag and push: `git tag -s v0.1.0 -m "platform-mcp-hub 0.1.0" && git push origin v0.1.0`.
5. Approve the `pypi` and `npm` environment deployments in the Actions run. The workflow builds once, checks the tag
   against the versions, publishes to PyPI (attestations on) and npm (`--provenance`), and attaches the artefacts to a
   GitHub release.
6. On a clean machine: `uvx platform-mcp-hub serve reed` and `npx -y platform-mcp-hub serve reed` start and list
   `me, search, get_posting` (`python tools/smoke_stdio.py` can drive both).

## Every release

- [ ] No open high-severity finding in `docs/SECURITY_REVIEW_*.md`.
- [ ] `release.yml` still has no `secrets.*`, only the publish jobs hold `id-token: write`, and they run in the
      protected environments (`tests/test_security_generators_python.py` checks this).

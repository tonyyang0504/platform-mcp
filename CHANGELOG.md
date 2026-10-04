# Changelog

All notable changes to platform-mcp-hub are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-04

First public release.

### Added
- One package, **platform-mcp-hub**, on PyPI and npm: the runtime, the whole catalog (3,500 platforms, 455 served in
  14 categories) and a CLI: `list`, `describe <id>`, `serve <id>` (stdio or `--http`), `serve --entry <file>` for
  entries you write yourself, and `directory` (the directory MCP server over the whole catalog).
- **Generic entries** (`"category": "generic"`): tools defined by the API's own operations (name, description,
  input schema, HTTP mapping), the answer passed through as `{data}` with optional field selection (`result.select`,
  per-call `select_fields`), in both runtimes with the same lint, smoke, try and live verification.
- Python-only authoring tools in the same CLI: `lint`, `try`, `smoke`, `verify` (live verification in both runtimes).
- Parity tests: for every served entry both runtimes build identical tools, and both CLIs give identical answers.
- Registry metadata per served entry (`servers/<category>/<id>/server.json`, MCPB `manifest.json`) pointing at
  `platform-mcp-hub serve <id>`.
- Release workflow with PyPI trusted publishing and npm provenance; CI, CodeQL, secret scanning, Dependabot.
- Open-source project files: Apache-2.0 licence and NOTICE, contributing guide with DCO sign-off, code of conduct,
  security policy, issue and pull request templates.

### Changed
- Replaces the 455 per-platform packages (`platform-mcp-<id>`, `@platform-mcp/<id>`) and `platform-mcp-core` /
  `platform-mcp-directory`, none of which were ever published. Credentials keep their names (`PLATFORM_MCP_<ID>_*`).
- The import package is `platform_mcp_hub` (was `platform_mcp_core`).

### Removed
- The forge (API docs → MCP server) was split out into a separate project, with its history.
- Internal provenance fields of the catalog (survey sources, private client and module names, proxy notes).

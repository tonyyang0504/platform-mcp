# platform-mcp-hub (npm)

The TypeScript runtime of [platform-mcp](https://github.com/tonyyang0504/platform-mcp): MCP servers for 450+ platform APIs
from one evidence-only catalog, with the same CLI as the Python package.

> **Unpublished.** This is the README npm will show once `platform-mcp-hub` is published. Until then, build it from a
> checkout: `cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js --help`.

```bash
npx platform-mcp-hub list                   # every served platform
npx platform-mcp-hub describe reed          # tools, credentials (PLATFORM_MCP_REED_*), run commands
npx platform-mcp-hub serve reed             # stdio MCP server
npx platform-mcp-hub serve reed --http      # Streamable HTTP on 127.0.0.1:8000/mcp
npx platform-mcp-hub serve --entry my.json  # an entry you wrote
npx platform-mcp-hub directory              # one server that searches the whole catalog
```

Python and TypeScript serve identical tools for every entry (the repository's parity tests check all of them). The
authoring tools (`lint`, `try`, `smoke`, `verify`) are in the Python package. Licence: Apache-2.0.

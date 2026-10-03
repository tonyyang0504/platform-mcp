"""The platform-mcp-hub CLI (Python): list, describe, serve <id>, serve --entry, directory, and every served catalog entry
built through the same code path `serve` uses. tests/cli.typescript.test.mjs checks the TypeScript CLI against these
answers (parity), so per-platform packages are not needed to cover each server."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub import __version__, catalog, cli  # noqa: E402
from platform_mcp_hub.server import build_server  # noqa: E402

ENV = {**os.environ, "PYTHONPATH": str(ROOT / "runtime" / "python")}


def run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "platform_mcp_hub", *args], capture_output=True, text=True, timeout=120, env=env or ENV)


def test_version_matches_the_npm_package():
    pkg = json.loads((ROOT / "runtime" / "typescript" / "package.json").read_text(encoding="utf-8"))
    ts = (ROOT / "runtime" / "typescript" / "src" / "version.ts").read_text(encoding="utf-8")
    import re
    pyproject = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)[1]
    assert pkg["version"] == __version__ == pyproject and f'"{__version__}"' in ts
    assert run_cli("--version").stdout.strip() == f"platform-mcp-hub {__version__}"


def test_list_json_counts_every_served_entry():
    out = json.loads(run_cli("list", "--json").stdout)
    served = [e for _, e in catalog.iter_entries(served_only=True)]
    assert out["total"] == len(served) == len(out["items"]) > 400
    reed = next(i for i in out["items"] if i["id"] == "reed")
    assert reed == {"id": "reed", "category": "jobs", "label": "Reed", "serve": "reed", "tools": ["me", "search", "get_posting"], "auth": "basic"}
    jobs = json.loads(run_cli("list", "--json", "--category", "jobs", "--query", "reed").stdout)
    assert [i["id"] for i in jobs["items"]] == ["reed"]


def test_describe_lists_credentials_and_run_commands():
    d = json.loads(run_cli("describe", "reed").stdout)
    assert d["env"][0]["name"] == "PLATFORM_MCP_REED_API_KEY" and d["env"][0]["isSecret"] is True
    assert d["serve"] == "reed" and d["registry_name"] == "io.github.tonyyang0504/reed-mcp"
    assert d["run"]["status"] == "unpublished" and d["run"]["python"] == "uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve reed"
    assert set(d["tools"]) == {"me", "search", "get_posting"} and "apply" in d["not_offered"]


def test_an_id_in_two_categories_needs_the_category():
    amb = run_cli("describe", "linkedin")
    assert amb.returncode == 2 and "several categories" in amb.stderr and "ads/linkedin" in amb.stderr
    for ref in (["social/linkedin"], ["linkedin", "--category", "social"]):
        d = json.loads(run_cli("describe", *ref).stdout)
        assert d["category"] == "social" and d["serve"] == "social/linkedin" and d["registry_name"].endswith("/linkedin-social-mcp")
    missing = run_cli("describe", "no_such_platform")
    assert missing.returncode == 2 and "no served entry" in missing.stderr
    bad = run_cli("serve", "../etc/passwd")
    assert bad.returncode == 2 and "not a platform id" in bad.stderr


def test_serve_entry_refuses_files_that_would_not_run(tmp_path):
    cases = {
        "not_json": "{",
        "no_adapter": json.dumps({"id": "x", "category": "jobs"}),
        "http": json.dumps({"id": "x", "category": "jobs", "adapter": {"base_url": "http://api.x.example", "tools": {"search": {"path": "/s"}}}}),
        "bad_verb": json.dumps({"id": "x", "category": "jobs", "adapter": {"base_url": "https://api.x.example", "tools": {"place_order": {"path": "/s"}}}}),
        "bad_id": json.dumps({"id": "X/../y", "category": "jobs", "adapter": {"base_url": "https://api.x.example", "tools": {"search": {"path": "/s"}}}}),
    }
    for name, text in cases.items():
        p = tmp_path / f"{name}.json"
        p.write_text(text, encoding="utf-8")
        res = run_cli("serve", "--entry", str(p))
        assert res.returncode == 2 and res.stderr.startswith("platform-mcp-hub: "), (name, res.stderr)
    assert "verbs not in the jobs vocabulary: place_order" in run_cli("describe", "--entry", str(tmp_path / "bad_verb.json")).stderr


async def _stdio_tools(args: list[str], env: dict) -> tuple[str, list]:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "platform_mcp_hub", *args], env=env)) as (r, w):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            return init.server_info.name, (await s.list_tools()).tools


@pytest.mark.asyncio
async def test_serve_id_and_serve_entry_speak_stdio(tmp_path):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ENV["PYTHONPATH"]}
    name, tools = await _stdio_tools(["serve", "reed"], env)
    assert name == "reed-mcp" and sorted(t.name for t in tools) == ["get_posting", "me", "search"]
    entry = json.loads((ROOT / "catalog" / "jobs" / "remotive.json").read_text(encoding="utf-8"))
    entry["id"] = "my_board"
    p = tmp_path / "my_board.json"
    p.write_text(json.dumps(entry), encoding="utf-8")
    name, tools = await _stdio_tools(["serve", "--entry", str(p)], env)
    assert name == "my_board-mcp" and sorted(t.name for t in tools) == sorted(entry["adapter"]["tools"])
    name, tools = await _stdio_tools(["directory"], env)
    assert name == "platform-mcp-hub-directory" and len(tools) == 4


def test_http_mode_keeps_the_bind_policy():
    res = run_cli("serve", "reed", "--http", "--host", "0.0.0.0")
    assert res.returncode == 2 and "refusing to serve HTTP" in res.stderr
    res = run_cli("directory", "--http", "--host", "0.0.0.0", "--allow-remote")
    assert res.returncode == 2 and "PLATFORM_MCP_HTTP_TOKEN" in res.stderr


@pytest.mark.asyncio
async def test_every_served_entry_builds_with_exactly_its_verbs():
    """What the 455 per-platform packages used to prove one by one: each entry is a working server."""
    n = 0
    for _, e in catalog.iter_entries(served_only=True):
        tools = await build_server(e).list_tools()
        assert sorted(t.name for t in tools) == sorted(e["adapter"]["tools"]), e["id"]
        assert all(t.title and t.annotations and t.input_schema.get("type") == "object" and t.output_schema for t in tools), e["id"]
        n += 1
    assert n > 400


def test_catalog_lookup_order(tmp_path, monkeypatch):
    monkeypatch.setenv(catalog.CATALOG_ENV, str(tmp_path))
    with pytest.raises(catalog.EntryError):
        catalog.catalog_dir()
    (tmp_path / "schema").mkdir()
    (tmp_path / "schema" / "vocab.json").write_text("{}")
    assert catalog.catalog_dir() == tmp_path.resolve()
    monkeypatch.delenv(catalog.CATALOG_ENV)
    assert catalog.catalog_dir() == ROOT / "catalog" and catalog.is_checkout()


def test_unknown_command_and_help():
    assert run_cli("frobnicate").returncode == 2
    h = run_cli("--help")
    assert h.returncode == 0 and "serve <id | category/id>" in h.stdout
    assert cli.main(["list", "--bogus"]) == 2

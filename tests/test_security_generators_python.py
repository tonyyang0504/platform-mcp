"""Security review 2026-10 (docs/SECURITY_REVIEW_2026-10.md): catalog strings must never become code or break out
of the generated registry metadata (server.json, manifest.json, README.md), and the lint refuses the values that could."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "python"))
from platform_mcp_hub import lint as lint_catalog  # noqa: E402

LABEL = 'Evil"""\nimport pathlib; pathlib.Path(__file__).with_name("PWNED").write_text("py")\n"""\r\u2028 */ require("fs").writeFileSync("PWNED_TS", "ts") //\\'


def _entry(**over) -> dict:
    e = {"id": "evil", "category": "jobs", "label": LABEL, "docs_url": "https://docs.evil.example/", "verified_at": "2026-10-01", "version": "0.1.0",
         "adapter": {"base_url": "https://api.evil.example", "auth": {"type": "none"}, "rate_per_second": 1,
                     "tools": {"get_posting": {"path": "/jobs/{id}", "result": {"fields": {"id": "id"}}, "docs": "https://docs.evil.example/jobs"}}}}
    e.update(over)
    return e


@pytest.fixture
def gen_ws(tmp_path):
    (tmp_path / "catalog" / "schema").mkdir(parents=True)
    (tmp_path / "catalog" / "jobs").mkdir()
    shutil.copy(ROOT / "catalog" / "schema" / "vocab.json", tmp_path / "catalog" / "schema" / "vocab.json")
    shutil.copytree(ROOT / "generators", tmp_path / "generators", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "runtime").symlink_to(ROOT / "runtime")
    return tmp_path


def _gen(ws: Path, entry: dict) -> subprocess.CompletedProcess:
    p = ws / "catalog" / "jobs" / f"{entry['id'] if '/' not in str(entry['id']) else 'evil'}.json"
    p.write_text(json.dumps(entry), encoding="utf-8")
    return subprocess.run([sys.executable, str(ws / "generators" / "python" / "gen.py"), str(p)], capture_output=True, text=True, timeout=60)


def test_a_hostile_label_stays_data_in_the_registry_metadata(gen_ws):
    py = _gen(gen_ws, _entry())
    assert py.returncode == 0, py.stderr
    base = gen_ws / "servers" / "jobs" / "evil"
    assert sorted(f.name for f in base.iterdir()) == ["README.md", "manifest.json", "server.json"]  # no code is generated at all
    sj = json.loads((base / "server.json").read_text(encoding="utf-8"))
    assert sj["description"].startswith(LABEL[:40]) and sj["packages"][0]["identifier"] == "platform-mcp-hub"
    assert [a["value"] for a in sj["packages"][0]["packageArguments"]] == ["serve", "evil"]
    mf = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    assert mf["display_name"] == f"{LABEL} MCP" and mf["server"]["mcp_config"]["args"] == ["platform-mcp-hub", "serve", "evil"]
    assert not list(gen_ws.rglob("PWNED*"))


@pytest.mark.parametrize("over", [
    {"version": '0.1.0"\n[tool.hatch.build.hooks.custom]\npath = "x.py'},
    {"version": "1"},
    {"id": "../../../escape"},
    {"category": "../jobs"},
])
def test_generators_refuse_unsafe_ids_categories_and_versions(gen_ws, over):
    py = _gen(gen_ws, _entry(**over))
    assert py.returncode != 0
    assert not (gen_ws / "servers").exists() or not any((gen_ws / "servers").rglob("*.json"))
    assert not (gen_ws.parent / "escape").exists()


def _lint(tmp_path: Path, entry: dict) -> list[str]:
    d = tmp_path / "catalog" / entry["category"]
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{entry['id']}.json"
    p.write_text(json.dumps(entry), encoding="utf-8")
    return lint_catalog.lint(p)[0]


@pytest.mark.parametrize("over,needle", [
    ({"label": "Evil\nimport os"}, "label"),
    ({"version": "0.1.0\"\nx"}, "version"),
    ({"adapter": {**_entry()["adapter"], "tools": {"get_posting": {"path": "http://api.evil.example/jobs/{id}", "result": {"fields": {"id": "id"}}, "docs": "https://d.example/"}}}}, "https"),
    ({"adapter": {**_entry()["adapter"], "auth": {"type": "oauth2_client_credentials", "token_url": "http://auth.evil.example/token", "fields": [{"name": "client_id", "help": "x"}]}}}, "token_url"),
    ({"adapter": {**_entry()["adapter"], "base_url": "https://169.254.169.254/latest"}}, "private"),
    ({"adapter": {**_entry()["adapter"], "base_url": "https://localhost:8443"}}, "private"),
    ({"adapter": {**_entry()["adapter"], "base_url": "https://[::1]/v1"}}, "private"),
    ({"adapter": {**_entry()["adapter"], "tools": {"get_posting": {"path": "https://10.0.0.8/jobs/{id}", "result": {"fields": {"id": "id"}}, "docs": "https://d.example/"}}}}, "private"),
])
def test_lint_refuses_code_like_strings_and_non_public_endpoints(tmp_path, over, needle):
    errors = _lint(tmp_path, {**_entry(label="Fine"), **over})
    assert any(needle in e for e in errors), errors


def test_lint_accepts_the_clean_entry(tmp_path):
    assert _lint(tmp_path, _entry(label="Fine Jobs (EU / UK)")) == []


# ---------------------------------------------------------------- SR-15: the release workflow (supply chain)

def test_release_workflow_uses_trusted_publishing_and_never_interpolates_inputs_into_scripts():
    import re
    import yaml
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(text)
    assert "secrets." not in text, "PyPI and npm publish through OIDC trusted publishing: no stored registry tokens"
    assert (wf.get("permissions") or {}) == {"contents": "read"}, "workflow-wide permissions stay read-only"
    for name, job in wf["jobs"].items():
        perms = job.get("permissions") or {}
        if perms.get("id-token") == "write":
            assert name.startswith("publish"), f"only publish jobs mint OIDC tokens ({name})"
            assert job.get("environment"), f"{name} publishes from a protected environment"
        for st in job.get("steps") or []:
            run = st.get("run") or ""
            assert "${{" not in run, f"{name}/{st.get('name')!r} interpolates an expression into its script"
            for cmd in re.findall(r"npm (?:ci|install|publish)[^\n;&|)]*", run):
                assert "--ignore-scripts" in cmd, cmd
            if "mcp-publisher" in run and "curl" in run:
                assert "sha256sum -c" in run and "releases/latest" not in json.dumps(st)
    for wf_file in (ROOT / ".github" / "workflows").glob("*.yml"):
        for job in (yaml.safe_load(wf_file.read_text(encoding="utf-8")).get("jobs") or {}).values():
            for step in job.get("steps") or []:
                assert "github.event.inputs" not in (step.get("run") or ""), wf_file.name

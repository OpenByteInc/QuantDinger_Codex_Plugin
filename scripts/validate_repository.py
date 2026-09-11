"""Validate the public distribution without contacting production services."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "quantdinger"


def main():
    catalog = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
    assert catalog["name"] == "quantdinger"
    assert len(catalog["plugins"]) == 2
    assert {item["name"] for item in catalog["plugins"]} == {"quantdinger", "quantdinger-macos"}
    for item in catalog["plugins"]:
        assert (ROOT / item["source"]["path"] / ".codex-plugin/plugin.json").is_file()
    entry = catalog["plugins"][0]
    assert entry["name"] == "quantdinger"
    assert entry["source"] == {"source": "local", "path": "./plugins/quantdinger"}
    assert entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert entry["category"] == "Finance"
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "quantdinger"
    assert re.fullmatch(r"\d+\.\d+\.\d+(\+codex\.[A-Za-z0-9.-]+)?", manifest["version"])
    assert manifest["license"] == "Apache-2.0"
    assert manifest["repository"] == "https://github.com/OpenByteInc/QuantDinger_Codex_Plugin"
    for field in ("skills", "mcpServers"):
        assert (PLUGIN / manifest[field]).exists(), field
    for field in ("composerIcon", "logo", "logoDark"):
        assert (PLUGIN / manifest["interface"][field]).is_file(), field

    runtime = json.loads((PLUGIN / "runtime/manifest.json").read_text(encoding="utf-8"))
    archive = PLUGIN / "runtime" / runtime["archive"]
    assert archive.stat().st_size == runtime["size_bytes"]
    with archive.open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == runtime["sha256"]
    with zipfile.ZipFile(archive) as packed:
        for name in ("connector.py", "connector-tools.json", "runtime-check.py"):
            assert packed.read("app/" + name) == (PLUGIN / "scripts" / name).read_bytes(), name
        inventory_bytes = packed.read("inventory.json")
        assert hashlib.sha256(inventory_bytes).hexdigest() == runtime["inventory_sha256"]
        assert any("license" in name.lower() for name in packed.namelist())

    wheels = json.loads((PLUGIN / "build/wheels-win-x64.lock.json").read_text(encoding="utf-8"))
    assert all(re.fullmatch(r"[a-f0-9]{64}", digest) for digest in wheels.values())
    assert any(name.startswith("quantdinger_mcp-" + runtime["mcp_version"] + "-") for name in wheels)
    runpy.run_path(str(ROOT / "scripts/sync_macos_plugin.py"))["sync"](check=True)

    forbidden = (".env", "config.json", ".pypirc", "credentials.json")
    markdown_count = 0
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in {".git", "__pycache__", "dist"} for part in relative.parts):
            continue
        if not path.is_file():
            continue
        assert path.name not in forbidden, relative
        assert "Microsoft" not in relative.parts, relative
        if path.suffix not in {".md", ".py", ".json", ".ps1", ".cmd", ".txt", ".yml", ".sh", ".lock", ".svg"}:
            continue
        content = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"pypi-[A-Za-z0-9_-]{40,}", content), relative
        assert not re.search(r"gh[pousr]_[A-Za-z0-9]{30,}", content), relative
        for token in re.findall(r"qd_agent_[A-Za-z0-9_-]{8,}", content):
            assert token.startswith(("qd_agent_fixture_", "qd_agent_never")), (relative, "non-fixture token")
        if path.suffix == ".md":
            markdown_count += 1
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                assert (path.parent / target.split("#", 1)[0]).exists(), (relative, target)
            for target in re.findall(r'<img[^>]+src="([^"]+)"', content):
                if target.startswith(("https://", "http://")):
                    continue
                assert (path.parent / target).is_file(), (relative, target)
    assert (ROOT / "README.zh-CN.md").exists()
    print(f"Validated catalog, runtime/source parity, locks and {markdown_count} Markdown files.")


if __name__ == "__main__":
    main()

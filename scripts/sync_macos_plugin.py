"""Build the Mac distribution from the canonical shared connector and skills."""
import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ROOT / "plugins/quantdinger"
MAC = ROOT / "plugins/quantdinger-macos"


def sync(check=False):
    shared = [Path("scripts/connector.py"), Path("scripts/connector-tools.json"), Path("tests/test_connector.py"), Path("LICENSE"), Path("NOTICE")]
    shared += [p.relative_to(WINDOWS) for folder in ("assets", "skills")
               for p in (WINDOWS / folder).rglob("*") if p.is_file()]
    for relative in shared:
        target = MAC / relative
        if check:
            assert target.read_bytes() == (WINDOWS / relative).read_bytes(), relative
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WINDOWS / relative, target)
    manifest = json.loads((WINDOWS / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    manifest["name"] = "quantdinger-macos"
    manifest["interface"]["displayName"] = "QuantDinger for Mac"
    target = MAC / ".codex-plugin/plugin.json"
    if check:
        assert json.loads(target.read_text(encoding="utf-8")) == manifest
    else:
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Mac shared source verified" if check else "Mac shared source synchronized")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    sync(parser.parse_args().check)

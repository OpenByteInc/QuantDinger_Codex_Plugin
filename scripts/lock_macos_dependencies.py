"""Pin PyPI wheel hashes for the macOS distribution; run only during release work."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
requirements = [line for line in (ROOT / "plugins/quantdinger/build/requirements-win-x64.txt").read_text().splitlines()
                if line and not line.lower().startswith(("pywin32",))]


def resolve(requirement):
    package, version = requirement.split("==")
    with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/{version}/json", timeout=30) as response:
        metadata = json.load(response)
    wheels = [item for item in metadata["urls"] if item["packagetype"] == "bdist_wheel"
              and ("-any.whl" in item["filename"] or "macosx" in item["filename"])]
    assert wheels, requirement
    hashes = sorted({item["digests"]["sha256"] for item in wheels})
    return requirement + " \\\n" + " \\\n".join("    --hash=sha256:" + value for value in hashes)


with ThreadPoolExecutor(max_workers=6) as pool:
    locked = list(pool.map(resolve, requirements))
destination = ROOT / "plugins/quantdinger-macos/runtime/requirements-macos.lock"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text("# Generated from pinned PyPI wheel metadata. Do not edit hashes by hand.\n" + "\n".join(locked) + "\n")
print(f"Locked {len(locked)} dependencies")

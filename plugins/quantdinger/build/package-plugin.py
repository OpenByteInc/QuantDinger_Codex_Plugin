"""Package only release inputs, excluding build caches and user state."""
import argparse
import hashlib
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
plugin = Path(__file__).resolve().parents[1]
output = args.output.resolve()
if output.is_relative_to(plugin):
    raise ValueError("release_output_must_be_outside_plugin")
output.parent.mkdir(parents=True, exist_ok=True)
roots = (".codex-plugin", ".mcp.json", "assets", "scripts", "skills", "runtime", "build", "tests", "README.md", "BUILDING.md", "LICENSE", "NOTICE")
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as packed:
    for name in roots:
        source = plugin / name
        paths = source.rglob("*") if source.is_dir() else [source]
        for path in sorted(paths):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                packed.write(path, "quantdinger/" + path.relative_to(plugin).as_posix(),
                             compress_type=zipfile.ZIP_STORED if path.suffix == ".zip" else zipfile.ZIP_DEFLATED)
with output.open("rb") as handle:
    checksum = hashlib.file_digest(handle, "sha256").hexdigest()
output.with_suffix(".zip.sha256").write_text(f"{checksum}  {output.name}\n", encoding="ascii")
print(f"Packaged {output} ({output.stat().st_size} bytes), SHA-256 {checksum}")

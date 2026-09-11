"""Build an offline Windows x64 runtime from pinned official Python and wheels."""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from pip._vendor.packaging.requirements import Requirement

PYTHON_VERSION = "3.13.15"
PYTHON_URL = "https://www.python.org/ftp/python/3.13.15/python-3.13.15-embeddable-amd64.zip"
PYTHON_SHA256 = "791ada5e20aba24524f8d939cdeb069976d632a699fe5cb65274b23f4545e68a"


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_file(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--mcp-wheel", type=Path)
    args = parser.parse_args()
    plugin = Path(__file__).resolve().parents[1]
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output = plugin / "runtime"
    output.mkdir(exist_ok=True)
    archive = work / "python-3.13.15-embeddable-amd64.zip"
    if not archive.exists():
        urllib.request.urlretrieve(PYTHON_URL, archive)
    if digest(archive) != PYTHON_SHA256:
        raise RuntimeError("python_archive_hash_mismatch")
    wheels = work / "wheels"
    wheels.mkdir(exist_ok=True)
    lock_path = plugin / "build/wheels-win-x64.lock.json"
    expected = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    if args.mcp_wheel:
        wheel = args.mcp_wheel.resolve()
        if not wheel.name.startswith("quantdinger_mcp-") or expected.get(wheel.name) != digest(wheel):
            raise RuntimeError("local_mcp_wheel_hash_mismatch")
        if wheel != wheels / wheel.name:
            shutil.copy2(wheel, wheels / wheel.name)
    cached = expected and all(Path(name).name == name and (wheels / name).is_file()
                              and digest(wheels / name) == sha for name, sha in expected.items())
    if not cached:
        subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                        "--no-deps", "--find-links", str(wheels), "--dest", str(wheels),
                        "-r", str(plugin / "build/requirements-win-x64.txt")], check=True)
    lock = {p.name: digest(p) for p in sorted(wheels.glob("*.whl"))}
    if lock_path.exists() and json.loads(lock_path.read_text()) != lock:
        raise RuntimeError("wheel_lock_mismatch")
    json_file(lock_path, lock)
    stage = Path(tempfile.mkdtemp(prefix="assembled-", dir=work))
    runtime = stage / "python"
    runtime.mkdir()
    with zipfile.ZipFile(archive) as incoming:
        incoming.extractall(runtime)
    (runtime / "python313._pth").write_text("python313.zip\n.\nLib/site-packages\nimport site\n", encoding="ascii")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-compile", "--no-deps", "--no-index",
                    "--find-links", str(wheels), "--target", str(runtime / "Lib/site-packages"),
                    "-r", str(plugin / "build/requirements-win-x64.txt")], check=True)
    installed = list(distributions(path=[str(runtime / "Lib/site-packages")]))
    versions = {d.metadata["Name"].lower().replace("_", "-"): d.version for d in installed}
    for distribution in installed:
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            version = versions.get(requirement.name.lower().replace("_", "-"))
            if not version or not requirement.specifier.contains(version):
                raise RuntimeError(f"unsatisfied_dependency: {distribution.metadata['Name']} -> {requirement}")
    app = stage / "app"
    app.mkdir()
    for filename in ("connector.py", "connector-tools.json", "runtime-check.py"):
        shutil.copy2(plugin / "scripts" / filename, app / filename)
    json_file(stage / "provenance.json", {"python_url": PYTHON_URL, "python_sha256": PYTHON_SHA256,
                                         "python_version": PYTHON_VERSION, "wheel_sha256": lock})
    shutil.copy2(plugin / "build/requirements-win-x64.txt", stage / "requirements.txt")
    (stage / "start-connector.cmd").write_text('@echo off\n"%~dp0python\\python.exe" -I "%~dp0app\\connector.py" %*\n', encoding="ascii")
    (stage / "NOTICE.txt").write_text(
        "QuantDinger Connector offline runtime for Windows 10/11 x64.\n"
        "No system Python, pip, PATH changes, or online package installation required.\n"
        "Run start-connector.cmd as an MCP stdio server, not as a graphical application.\n"
        "Python license: python/LICENSE.txt. Dependency licenses: python/Lib/site-packages/*.dist-info/.\n"
        "Customer credentials are not included. Chat-provided tokens remain in chat/tool history.\n",
        encoding="utf-8")
    python = runtime / "python.exe"
    subprocess.run([str(python), "-I", str(app / "runtime-check.py")], check=True)
    # Pip-generated console wrappers embed the build interpreter path; use our launcher instead.
    console_wrappers = runtime / "Lib/site-packages/bin"
    inventory = {p.relative_to(stage).as_posix(): digest(p) for p in sorted(stage.rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
                 and not p.is_relative_to(console_wrappers)}
    json_file(stage / "inventory.json", inventory)
    packed = output / "quantdinger-runtime-win-x64.zip"
    with zipfile.ZipFile(packed, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for relative in sorted([*inventory, "inventory.json"]):
            info = zipfile.ZipInfo(relative, date_time=(2026, 9, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, (stage / relative).read_bytes())
    sha = digest(packed)
    mcp_version = versions["quantdinger-mcp"]
    json_file(output / "manifest.json", {"schema": 1, "platform": "win-x64",
        "runtime_id": f"win-x64-py{PYTHON_VERSION}-mcp{mcp_version}-{sha[:16]}",
        "archive": packed.name, "sha256": sha, "size_bytes": packed.stat().st_size,
        "inventory_sha256": digest(stage / "inventory.json"), "python_version": PYTHON_VERSION,
        "mcp_version": mcp_version})
    print(json.dumps({"archive": str(packed), "bytes": packed.stat().st_size, "sha256": sha, "stage": str(stage)}))


if __name__ == "__main__":
    main()

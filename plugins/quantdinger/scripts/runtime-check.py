"""Offline import and isolation checks; never load customer credentials."""
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import sys


def main():
    modules = ("ssl", "sqlite3", "ctypes", "httpx", "mcp", "jsonschema", "keyring",
               "cryptography", "pydantic_core", "win32api", "pythoncom", "win32ctypes.pywin32")
    for name in modules:
        importlib.import_module(name)
    root = Path(sys.executable).resolve().parent
    if not sys.flags.isolated or any(not Path(p).resolve().is_relative_to(root) for p in sys.path):
        raise RuntimeError("runtime_not_isolated")
    print(json.dumps({"status": "ready", "python": sys.version.split()[0],
                      "mcp": version("quantdinger-mcp"), "isolated": True,
                      "executable": str(Path(sys.executable).resolve())}))


if __name__ == "__main__":
    main()

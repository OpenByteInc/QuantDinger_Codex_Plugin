"""Check the isolated macOS runtime without reading account credentials."""
import importlib.metadata
from pathlib import Path
import re
import sys

assert sys.platform == "darwin", "macos_required"
assert sys.version_info[:2] == (3, 13), "python_313_required"
assert sys.prefix != sys.base_prefix, "isolated_environment_required"
for line in Path(sys.argv[1]).read_text().splitlines():
    requirement = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", line)
    if requirement:
        assert importlib.metadata.version(requirement[1]) == requirement[2], requirement[1]
import httpx
import jsonschema
import keyring.backends.macOS
import mcp
assert keyring.backends.macOS.Keyring.priority > 0
print("macos_runtime_verified")

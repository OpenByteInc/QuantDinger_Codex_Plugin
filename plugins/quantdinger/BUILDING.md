# Offline Windows x64 runtime

The release is a self-contained runtime, not a copied virtual environment. Python's official embeddable distribution does not depend on the build machine's Python installation or registry paths.

## Inputs

- Official Python 3.13.15 Windows x64 embeddable archive; URL and SHA-256 are pinned in `build/build-runtime.py` using the [Python release manifest](https://www.python.org/ftp/python/3.13.15/windows-3.13.15.json).
- `build/requirements-win-x64.txt`: all dependency versions, including MCP and credential-storage/native libraries.
- `build/wheels-win-x64.lock.json`: exact wheel filenames and SHA-256 hashes. Rebuilds reject a different wheel set or hash.
- Connector source and metadata in `scripts/`.

Python's [embedded distribution guidance](https://docs.python.org/3.13/using/windows.html#the-embeddable-package) recommends shipping third-party packages with the application. No pip is included in the customer runtime. Python's license and dependency distribution metadata/licenses are preserved in the archive.

## Build (maintainer only)

Use a Windows x64 Python 3.13 build interpreter with pip:

```powershell
python build/build-runtime.py --work-dir C:/build/quantdinger-runtime
```

The builder verifies Python's hash, downloads pinned binary wheels, verifies the wheel lock, installs them into a fresh staging directory, checks dependency requirements, runs an offline isolated import check, and creates `runtime/quantdinger-runtime-win-x64.zip` plus `runtime/manifest.json`. The build folder is distinct from the user's Connector configuration; no customer credentials or state are copied.

Use a dedicated work directory. Build staging directories are retained for inspection and are not shipped. To change dependencies, intentionally update both the pinned requirement list and the reviewed wheel lock. Updating a runtime bundle requires regenerating its manifest and testing the complete artifact.

For an unpublished MCP patch, build its wheel from the backend repository, update the MCP requirement and its wheel hash in the lock, then pass `--mcp-wheel <wheel-path>`. The builder verifies the local wheel against that lock before copying it into the download cache. The runtime version is derived from installed package metadata. This does not publish the wheel to PyPI.

## Customer launch

1. The plugin's CMD entrypoint invokes the built-in Windows PowerShell bootstrap.
2. The bootstrap selects the bundled x64 runtime, verifies its archive hash, validates extraction paths, and extracts to a fresh staging directory.
3. Every packaged file is checked against the hashed inventory, then the offline import/isolation check must succeed.
4. Only a successful staging directory is promoted to a hash-derived immutable runtime path. Failed installs do not replace a working earlier runtime or touch connection settings.
5. The launcher runs the package's own Python in isolated mode. Python discovery, pip, administrator elevation and PATH edits are not part of this flow.

Warm starts verify the inventory and critical Python/Connector files. `install-connector.ps1 -RefreshRuntime` additionally verifies every packaged file. A corrupted cached runtime is moved to a uniquely named quarantine directory rather than deleted. Older version directories remain available for rollback by reinstalling the previous plugin bundle.

## Tests

Run `tests/test_connector.py` and `tests/test_bundle.py` using the extracted private `python/python.exe -I`. The bundle suite removes Python/py/pip from PATH, sets invalid PYTHONHOME/PYTHONPATH, prevents external HTTP bootstrap using an unreachable proxy, uses a fresh LOCALAPPDATA directory, and checks real MCP initialization, generated-token connection/rotation, parallel extraction, damaged archive rejection, cache repair, and ZIP path traversal rejection. Fixtures contact only a local HTTP test server, not production QuantDinger.

These tests do not constitute clean-VM certification or publisher signing. The Python executable's upstream signature is distinct from signing the complete QuantDinger package. This plugin is distributed through a GitHub marketplace, separately from OpenAI's reviewed public directory. macOS, Linux and ARM64 releases are not included.

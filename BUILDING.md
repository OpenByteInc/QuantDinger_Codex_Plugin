# Build and test

## Layout

```text
.agents/plugins/marketplace.json   Git marketplace catalog
plugins/quantdinger/               Installable plugin root
  .codex-plugin/plugin.json        Identity and discovery metadata
  .mcp.json                       Windows stdio launcher configuration
  skills/                         Connection, strategy and operations workflows
  scripts/                        Credential connector and bootstrap
  runtime/                        Pinned Windows archive and integrity manifest
  build/                          Rebuild scripts and dependency locks
  tests/                          Local fixture-based regression tests
scripts/validate_repository.py     Distribution and documentation checks
```

The runtime archive is deliberately included in Git to make marketplace installation complete without a separate download step. Do not use Git LFS unless the client checkout workflow has been verified to retrieve LFS objects.

## Validate repository inputs

Use Python 3.13 from the repository root:

```powershell
python scripts/validate_repository.py
```

The validator checks catalog paths, manifest versions, local Markdown links, archive size/hash, bundled connector/source parity, dependency locks and accidental secret or state files. It uses only the Python standard library.

## Run Windows regression tests

```powershell
$qdRuntime = & .\plugins\quantdinger\scripts\install-connector.ps1 -PrintRuntime
& "$qdRuntime\python\python.exe" -I -m unittest discover -s plugins/quantdinger/tests -p "test_*.py" -v
```

The suite uses a loopback HTTP fixture and dummy tokens. It exercises credential validation and rotation, MCP initialization, offline bootstrap with no system Python, concurrent extraction, corrupt-cache repair and archive traversal rejection. It does not run trades or backtests on production accounts. CI runs the same suite on Windows.

These tests do not constitute macOS validation, a signed-installer certification, or an end-to-end live-trading test.

## Rebuild the Windows runtime

Use Windows x64 Python 3.13 with pip:

```powershell
python plugins/quantdinger/build/build-runtime.py --work-dir "$env:TEMP\quantdinger-runtime-build"
```

Python's official embeddable archive and each dependency wheel are hash-pinned. The builder downloads the pinned artifacts, validates the wheel set, assembles a fresh runtime, preserves third-party license metadata, runs an isolated import check and writes the archive plus manifest.

Review changes to both `requirements-win-x64.txt` and `wheels-win-x64.lock.json` when updating dependencies. Connector source is embedded in the runtime, so a connector change requires rebuilding that archive. Never copy an existing user runtime or credential directory into a release.

An unpublished upstream MCP wheel can be supplied with `--mcp-wheel <path>` only after intentionally updating the pin and expected hash. This does not publish to PyPI.

## Create a standalone plugin archive

```powershell
python plugins/quantdinger/build/package-plugin.py --output dist/quantdinger-codex-plugin-0.1.0-windows-x64.zip
```

The resulting archive includes the plugin folder and a SHA-256 companion file. For Git-based installation, use the repository marketplace. For a standalone archive, extract `quantdinger` under a local marketplace's `plugins/` directory and register that marketplace as described in the official packaging guide.

Before a release, update plugin metadata, both README files and the changelog; rebuild when runtime inputs change; run validation and regression tests; then test a fresh Git checkout. Keep MCP and plugin version numbers distinct. Only publish platform claims supported by completed checks.

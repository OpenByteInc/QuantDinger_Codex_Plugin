# Build and test

## Layout

```text
.agents/plugins/marketplace.json   Git marketplace catalog
plugins/quantdinger/               Installable Windows plugin root
  .codex-plugin/plugin.json        Identity and discovery metadata
  .mcp.json                       Windows stdio launcher configuration
  skills/                         Connection, strategy and operations workflows
  scripts/                        Credential connector and bootstrap
  runtime/                        Pinned Windows archive and integrity manifest
  build/                          Rebuild scripts and dependency locks
  tests/                          Local fixture-based regression tests
scripts/validate_repository.py     Distribution and documentation checks
plugins/quantdinger-macos/         Mac launcher, lock and native tests
scripts/sync_macos_plugin.py       Shared connector/skills/assets parity
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

These tests do not constitute signed-installer certification or an end-to-end live-trading test.

## Run Mac regression tests

On a Mac with uv installed:

```bash
qd_python="$(/bin/bash plugins/quantdinger-macos/scripts/launch-quantdinger.sh --print-python)"
"$qd_python" -I scripts/validate_repository.py
"$qd_python" -I -m unittest discover -s plugins/quantdinger-macos/tests -p 'test_*.py' -v
```

CI runs on Apple Silicon (`macos-15`). Tests cover the shared MCP protocol, native Keychain set/get/update/delete, cold setup in a path with spaces and Unicode, credential rotation, and a warm launch with unavailable network proxies. CI creates a disposable default keychain on the ephemeral runner; do not copy that CI setup into user onboarding. These are real macOS runtime tests, not a manual Codex desktop UI certification. Intel was tested during development and rejected because cryptography 50.0.1 has no official Intel macOS wheel; the launcher now rejects that architecture before downloading anything.

The canonical connector, tool definitions, workflow skills and assets live in the Windows entry. After changing them, run `python scripts/sync_macos_plugin.py`; validation enforces byte parity with the Mac entry. Native launchers and platform tests remain separate.

To intentionally update Mac dependencies, update/review the canonical pins, then run `python scripts/lock_macos_dependencies.py`. This queries PyPI for compatible macOS/universal wheel hashes and omits Windows-only packages. Review and commit the resulting lock; installation uses `--require-hashes --only-binary :all:`. Python is constrained to managed 3.13, with the patch version selected by uv. Repeat macOS tests after any lock or launcher change.

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
python plugins/quantdinger/build/package-plugin.py --output dist/quantdinger-codex-plugin-0.2.0-windows-x64.zip
```

The resulting archive includes the plugin folder and a SHA-256 companion file. For Git-based installation, use the repository marketplace. For a standalone archive, extract `quantdinger` under a local marketplace's `plugins/` directory and register that marketplace as described in the official packaging guide.

Before a release, update plugin metadata, both README files and the changelog; rebuild when runtime inputs change; run validation and regression tests; then test a fresh Git checkout. Keep MCP and plugin version numbers distinct. Only publish platform claims supported by completed checks.

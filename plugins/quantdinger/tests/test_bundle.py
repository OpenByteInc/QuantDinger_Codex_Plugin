"""Exercise the shipped archive with no Python on PATH and no online bootstrap."""
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_connector import FixtureHandler, TOKEN_A, TOKEN_B, TOKEN_BAD, data
import connector
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PLUGIN = Path(__file__).resolve().parents[1]
POWERSHELL = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
CMD = str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe")


def isolated_environment(root):
    root.mkdir(parents=True, exist_ok=True)
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "COMSPEC", "PROCESSOR_ARCHITECTURE") if key in os.environ}
    env.update({"PATH": str(Path(os.environ["SystemRoot"]) / "System32"),
        "LOCALAPPDATA": str(root / "local"), "APPDATA": str(root / "roaming"),
        "USERPROFILE": str(root / "profile"), "TEMP": str(root), "TMP": str(root),
        "PYTHONHOME": str(root / "missing-python"), "PYTHONPATH": str(root / "poison"),
        "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9", "NO_PROXY": "127.0.0.1,localhost",
        "QUANTDINGER_AGENT_TOKEN": "", "QUANTDINGER_BASE_URL": ""})
    return env


def install(plugin, env, refresh=False):
    args = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(plugin / "scripts/install-connector.ps1"), "-PrintRuntime"]
    if refresh:
        args.append("-RefreshRuntime")
    return subprocess.run(args, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


@asynccontextmanager
async def packaged_session(env, errors):
    config = json.loads((PLUGIN / ".mcp.json").read_text())["mcpServers"]["quantdinger"]
    parameters = StdioServerParameters(command=CMD, args=config["args"], cwd=str(PLUGIN), env=env)
    async with stdio_client(parameters, errlog=errors) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=180)) as session:
            await session.initialize()
            yield session


class OfflineBundleTests(unittest.IsolatedAsyncioTestCase):
    async def test_cold_install_connect_rotate_with_no_python_on_path(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        accounts = set()
        with tempfile.TemporaryDirectory(prefix="qd-bundle-") as directory:
            root = Path(directory) / "space and unicode 用户"
            env = isolated_environment(root)
            env["QUANTDINGER_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
            for command in ("python", "python3", "py", "pip"):
                self.assertIsNone(shutil.which(command, path=env["PATH"]))
            config_path = Path(env["LOCALAPPDATA"]) / "QuantDinger/Connector/config.json"
            started = time.perf_counter()
            try:
                with (root / "protocol-stderr.txt").open("w+") as errors:
                    async with packaged_session(env, errors) as session:
                        listed = await session.list_tools()
                        self.assertEqual(len(listed.tools), 60)
                        self.assertEqual(data(await session.call_tool("connection_status", {}))["status"], "not_connected")
                        self.assertEqual(server.requests, [])
                        for token, identity in ((TOKEN_A, 101), (TOKEN_B, 202)):
                            response = await session.call_tool("connect_quantdinger", {"agent_token": token})
                            if config_path.exists():
                                accounts.add(json.loads(config_path.read_text())["credential_account"])
                            self.assertFalse(response.isError, response.model_dump_json())
                            self.assertFalse(data(response)["restart_required"])
                            self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], identity)
                        rejected = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_BAD})
                        self.assertTrue(rejected.isError)
                        self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
                    errors.seek(0)
                    output = errors.read()
                    self.assertNotIn("Traceback", output)
                    for token in (TOKEN_A, TOKEN_B, TOKEN_BAD):
                        self.assertNotIn(token, output)
                self.assertTrue(all(method == "GET" for method, _, _ in server.requests))
                warm = install(PLUGIN, env)
                self.assertEqual(warm.returncode, 0, warm.stderr)
                runtime = Path(warm.stdout.strip())
                checked = subprocess.run([str(runtime / "python/python.exe"), "-I", str(runtime / "app/runtime-check.py")],
                    env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertTrue(json.loads(checked.stdout)["isolated"])
                print(f"Offline cold-install + same-session connection/rotation passed in {time.perf_counter()-started:.1f}s")
            finally:
                for account in accounts:
                    connector.keyring.delete_password(connector.SECRET_SERVICE, account)

    async def test_parallel_install_and_cached_repair_preserve_settings(self):
        with tempfile.TemporaryDirectory(prefix="qd-bundle-repair-") as directory:
            root = Path(directory)
            env = isolated_environment(root)
            first, second = await asyncio.gather(asyncio.to_thread(install, PLUGIN, env), asyncio.to_thread(install, PLUGIN, env))
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            target = Path(first.stdout.strip())
            self.assertTrue((target / ".complete").exists())
            settings = Path(env["LOCALAPPDATA"]) / "QuantDinger/Connector/config.json"
            settings.write_text('{"fixture_preserve": true}')
            corrupt = target / "app/connector.py"
            corrupt.write_text("raise RuntimeError('fixture_corruption')")
            repaired = await asyncio.to_thread(install, PLUGIN, env)
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            self.assertEqual(settings.read_text(), '{"fixture_preserve": true}')
            self.assertNotIn("fixture_corruption", corrupt.read_text())
            self.assertEqual(len(list(target.parent.glob("quarantine-*"))), 1)

    async def test_bad_archive_rejected_without_affecting_existing_install(self):
        with tempfile.TemporaryDirectory(prefix="qd-bundle-bad-") as directory:
            root = Path(directory)
            env = isolated_environment(root / "user")
            fake_plugin = root / "fixture-plugin"
            (fake_plugin / "scripts").mkdir(parents=True)
            (fake_plugin / "runtime").mkdir()
            shutil.copy2(PLUGIN / "scripts/install-connector.ps1", fake_plugin / "scripts/install-connector.ps1")
            manifest = json.loads((PLUGIN / "runtime/manifest.json").read_text())
            (fake_plugin / "runtime/manifest.json").write_text(json.dumps(manifest))
            (fake_plugin / "runtime" / manifest["archive"]).write_bytes(b"fixture_corrupt_archive")
            versions = Path(env["LOCALAPPDATA"]) / "QuantDinger/Connector/runtimes"
            previous = versions / "previous-working-fixture"
            previous.mkdir(parents=True)
            (previous / ".complete").write_text("previous-working-fixture")
            attempt = await asyncio.to_thread(install, fake_plugin, env)
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn("runtime_archive_hash_mismatch", attempt.stderr)
            self.assertEqual(list(versions.glob("*/.complete")), [previous / ".complete"])
            self.assertEqual((previous / ".complete").read_text(), "previous-working-fixture")

    async def test_unsupported_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qd-bundle-arch-") as directory:
            env = isolated_environment(Path(directory))
            env["PROCESSOR_ARCHITECTURE"] = "ARM64"
            attempt = await asyncio.to_thread(install, PLUGIN, env)
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn("unsupported_runtime_platform_win_x64_required", attempt.stderr)

    async def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qd-bundle-path-") as directory:
            root = Path(directory)
            env = isolated_environment(root / "user")
            plugin = root / "fixture-plugin"
            (plugin / "scripts").mkdir(parents=True)
            (plugin / "runtime").mkdir()
            shutil.copy2(PLUGIN / "scripts/install-connector.ps1", plugin / "scripts/install-connector.ps1")
            manifest = json.loads((PLUGIN / "runtime/manifest.json").read_text())
            archive = plugin / "runtime" / manifest["archive"]
            with zipfile.ZipFile(archive, "w") as packed:
                packed.writestr("../../escaped.txt", "fixture")
            manifest["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
            (plugin / "runtime/manifest.json").write_text(json.dumps(manifest))
            attempt = await asyncio.to_thread(install, plugin, env)
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn("archive_path_escape", attempt.stderr)
            self.assertEqual(list(root.rglob("escaped.txt")), [])

    async def test_archive_has_no_credentials_and_matches_connector_source(self):
        manifest = json.loads((PLUGIN / "runtime/manifest.json").read_text())
        archive = PLUGIN / "runtime" / manifest["archive"]
        with archive.open("rb") as handle:
            self.assertEqual(hashlib.file_digest(handle, "sha256").hexdigest(), manifest["sha256"])
        with zipfile.ZipFile(archive) as packed:
            self.assertEqual(packed.read("app/connector.py"), (PLUGIN / "scripts/connector.py").read_bytes())
            self.assertIn("python/LICENSE.txt", packed.namelist())
            self.assertFalse(any(name.endswith(("config.json", "fake-vault.json", ".pyc")) for name in packed.namelist()))
            self.assertFalse(any(name.startswith("python/Lib/site-packages/pip/") for name in packed.namelist()))
            self.assertFalse(any(name.startswith("python/Lib/site-packages/bin/") for name in packed.namelist()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

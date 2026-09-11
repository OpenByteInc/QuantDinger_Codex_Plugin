"""macOS bootstrap and native Keychain checks on real Apple Silicon runners."""
import asyncio
from datetime import timedelta
import faulthandler
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_connector import FixtureHandler, TOKEN_A, TOKEN_B, TOKEN_BAD, connector, data
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PLUGIN = Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform == "darwin", "macOS runner required")
class MacTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        faulthandler.dump_traceback_later(90, repeat=True)
        self.addCleanup(faulthandler.cancel_dump_traceback_later)

    async def test_native_keychain_roundtrip(self):
        from keyring.backends.macOS import Keyring
        vault = Keyring()
        service = "QuantDinger CI " + uuid.uuid4().hex
        vault.set_password(service, "fixture", TOKEN_A)
        try:
            self.assertEqual(vault.get_password(service, "fixture"), TOKEN_A)
            vault.set_password(service, "fixture", TOKEN_B)
            self.assertEqual(vault.get_password(service, "fixture"), TOKEN_B)
        finally:
            vault.delete_password(service, "fixture")
        self.assertIsNone(vault.get_password(service, "fixture"))

    async def test_application_support_path(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": "/invalid-windows-path"}):
            self.assertEqual(connector.connector_root(), Path.home() / "Library/Application Support/QuantDinger/Connector")

    async def test_cold_bootstrap_and_offline_warm_start(self):
        with tempfile.TemporaryDirectory(prefix="qd-mac-") as temp:
            root = Path(temp) / "space and unicode 用户"
            root.mkdir()
            checkout = root / "plugin"
            shutil.copytree(PLUGIN, checkout, ignore=shutil.ignore_patterns("__pycache__"))
            env = {**os.environ, "HOME": str(root), "PYTHONHOME": "/nonexistent/poison",
                   "PYTHONPATH": "/nonexistent/poison"}
            args = ["/bin/bash", str(checkout / "scripts/launch-quantdinger.sh"), "--print-python"]
            boot = await asyncio.to_thread(subprocess.run, args, env=env, text=True,
                                           capture_output=True, timeout=180)
            self.assertEqual(boot.returncode, 0, boot.stderr)
            self.assertTrue(Path(boot.stdout.strip()).is_file())
            self.assertTrue(Path(boot.stdout.strip()).is_relative_to(root.resolve()))
            env.update({"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
                        "ALL_PROXY": "http://127.0.0.1:9"})
            warm = await asyncio.to_thread(subprocess.run, args, env=env, text=True,
                                           capture_output=True, timeout=60)
            self.assertEqual(warm.returncode, 0, warm.stderr)
            self.assertEqual(warm.stdout, boot.stdout)
            self.assertFalse((root / "Library/Application Support/QuantDinger/Connector/config.json").exists())
            print("Cold bootstrap and offline warm start verified in a fresh Unicode home", flush=True)

    @unittest.skipUnless(os.environ.get("GITHUB_ACTIONS") == "true", "Requires a clean CI user and disposable Keychain")
    async def test_packaged_native_connection_rotation(self):
        settings = connector.connector_root() / "config.json"
        self.assertFalse(settings.exists(), "Refusing to replace an existing connection")
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        accounts = set()
        with tempfile.TemporaryDirectory(prefix="qd-mac-protocol-") as temp:
            root = Path(temp)
            checkout = root / "plugin with spaces 用户"
            shutil.copytree(PLUGIN, checkout, ignore=shutil.ignore_patterns("__pycache__"))
            env = {**os.environ, "QUANTDINGER_AGENT_TOKEN": "",
                   "QUANTDINGER_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                   "PYTHONHOME": "/nonexistent/poison", "PYTHONPATH": "/nonexistent/poison"}
            definition = json.loads((checkout / ".mcp.json").read_text())["mcpServers"]["quantdinger"]
            params = StdioServerParameters(command=definition["command"], args=definition["args"],
                                          cwd=str(checkout), env=env)
            error_path = root / "protocol-errors.log"
            try:
                with error_path.open("w+") as errors:
                    async with stdio_client(params, errlog=errors) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as session:
                            await session.initialize()
                            self.assertEqual(len((await session.list_tools()).tools), 60)
                            self.assertEqual(server.requests, [])
                            for token, identity in ((TOKEN_A, 101), (TOKEN_B, 202)):
                                print(f"Connecting fixture identity {identity} using the login user's native Keychain", flush=True)
                                response = await session.call_tool("connect_quantdinger", {"agent_token": token})
                                if settings.exists():
                                    accounts.add(json.loads(settings.read_text())["credential_account"])
                                self.assertFalse(response.isError, data(response))
                                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], identity)
                            rejected = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_BAD})
                            self.assertTrue(rejected.isError)
                            self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
                    async with stdio_client(params, errlog=errors) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as session:
                            await session.initialize()
                            self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
                    errors.flush()
                    for token in (TOKEN_A, TOKEN_B, TOKEN_BAD):
                        self.assertNotIn(token, error_path.read_text())
                        self.assertNotIn(token, settings.read_text())
                self.assertTrue(all(method == "GET" for method, _, _ in server.requests))
                print("Native connection, rotation, rejected replacement and restart persistence verified", flush=True)
            except BaseException:
                print(connector.redact(error_path.read_text()), flush=True)
                raise
            finally:
                if settings.exists() and json.loads(settings.read_text()).get("credential_account") in accounts:
                    settings.unlink()
                for account in accounts:
                    connector.keyring.delete_password(connector.SECRET_SERVICE, account)


if __name__ == "__main__":
    unittest.main(verbosity=2)

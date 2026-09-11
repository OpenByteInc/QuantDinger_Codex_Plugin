"""macOS launcher, warm-start and native Keychain checks on real Mac runners."""
import asyncio
import faulthandler
from datetime import timedelta
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

    async def test_cold_launch_rotation_and_offline_warm_start(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        accounts = set()
        with tempfile.TemporaryDirectory(prefix="qd-mac-") as temp:
            root = Path(temp) / "space and unicode 用户"
            root.mkdir()
            checkout = root / "plugin"
            shutil.copytree(PLUGIN, checkout, ignore=shutil.ignore_patterns("__pycache__"))
            env = {**os.environ, "HOME": str(root), "QUANTDINGER_AGENT_TOKEN": "",
                   "QUANTDINGER_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                   "PYTHONHOME": "/nonexistent/poison", "PYTHONPATH": "/nonexistent/poison"}
            settings = root / "Library/Application Support/QuantDinger/Connector/config.json"
            definition = json.loads((checkout / ".mcp.json").read_text())["mcpServers"]["quantdinger"]
            boot = await asyncio.to_thread(subprocess.run,
                ["/bin/bash", str(checkout / "scripts/launch-quantdinger.sh"), "--print-python"],
                env=env, text=True, capture_output=True, timeout=180)
            self.assertEqual(boot.returncode, 0, boot.stderr)
            test_python = boot.stdout.strip()
            self.assertTrue(Path(test_python).is_file())
            print("Mac cold bootstrap completed in a fresh Unicode home", flush=True)
            if os.environ.get("GITHUB_ACTIONS") == "true":
                ci_keychain = Path(os.environ["RUNNER_TEMP"]) / "qd-ci.keychain-db"
                self.assertTrue(ci_keychain.is_file())
                for operation in ("default-keychain", "list-keychains"):
                    configured = subprocess.run(["security", operation, "-d", "user", "-s", str(ci_keychain)],
                        env=env, text=True, capture_output=True, timeout=15)
                    self.assertEqual(configured.returncode, 0, configured.stderr)
            params = StdioServerParameters(command=definition["command"], args=definition["args"],
                                          cwd=str(checkout), env=env)
            try:
                with (root / "protocol-errors.log").open("w+") as errors:
                    async with stdio_client(params, errlog=errors) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=120)) as session:
                            await session.initialize()
                            print("Mac MCP initialized", flush=True)
                            self.assertEqual(len((await session.list_tools()).tools), 60)
                            self.assertEqual(server.requests, [])
                            for token, identity in ((TOKEN_A, 101), (TOKEN_B, 202)):
                                print(f"Checking native-vault connection for fixture identity {identity}", flush=True)
                                response = await session.call_tool("connect_quantdinger", {"agent_token": token})
                                self.assertFalse(response.isError, data(response))
                                accounts.add(json.loads(settings.read_text())["credential_account"])
                                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], identity)
                            rejected = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_BAD})
                            self.assertTrue(rejected.isError)
                            self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
                            print("Mac credential rotation and rejected replacement verified", flush=True)
                    errors.flush()
                    output = (root / "protocol-errors.log").read_text()
                    for token in (TOKEN_A, TOKEN_B, TOKEN_BAD):
                        self.assertNotIn(token, output)
                        self.assertNotIn(token, settings.read_text())
                env.update({"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
                            "ALL_PROXY": "http://127.0.0.1:9"})
                warm = subprocess.run(["/bin/bash", str(checkout / "scripts/launch-quantdinger.sh"), "--print-python"],
                                      env=env, text=True, capture_output=True, timeout=60)
                self.assertEqual(warm.returncode, 0, warm.stderr)
                self.assertTrue(Path(warm.stdout.strip()).is_file())
                self.assertTrue(all(method == "GET" for method, _, _ in server.requests))
            finally:
                if accounts:
                    cleanup = subprocess.run([test_python, "-I", "-c",
                        "import json,keyring,sys; [keyring.delete_password('QuantDinger Connector', account) for account in json.load(sys.stdin)]"],
                        input=json.dumps(sorted(accounts)), text=True, capture_output=True, timeout=30)
                    self.assertEqual(cleanup.returncode, 0, cleanup.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

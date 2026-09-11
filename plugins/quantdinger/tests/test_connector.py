"""Isolated tests: generated credentials only; no production account access."""
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import connector
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TOKEN_A = "qd_agent_fixture_identity_A_00000000"
TOKEN_B = "qd_agent_fixture_identity_B_00000000"
TOKEN_BAD = "qd_agent_fixture_invalid_00000000"
IDENTITY = {"user_id": 101, "scopes": ["R"], "paper_only": True, "markets": ["Crypto"]}


class MemoryVault:
    def __init__(self):
        self.values = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, password):
        self.values[service, account] = password

    def delete_password(self, service, account):
        del self.values[service, account]


class FixtureVault(MemoryVault):
    """Plaintext fake-token storage strictly under the test temporary directory."""
    def __init__(self, root):
        super().__init__()
        self.path = Path(root) / "fake-vault.json"

    def get_password(self, service, account):
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text()).get(service + "/" + account)

    def set_password(self, service, account, password):
        data = json.loads(self.path.read_text()) if self.path.exists() else {}
        data[service + "/" + account] = password
        self.path.write_text(json.dumps(data))

    def delete_password(self, service, account):
        data = json.loads(self.path.read_text())
        del data[service + "/" + account]
        self.path.write_text(json.dumps(data))


def data(response):
    value = response.structuredContent
    if value is None:
        value = json.loads(response.content[0].text)
    if isinstance(value, dict) and set(value) == {"result"}:
        return value["result"]
    return value


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qd-connector-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = MemoryVault()
        self.creds = connector.Credentials(self.root, self.vault)
        self.environment = patch.dict(os.environ, {"QUANTDINGER_AGENT_TOKEN": "", "QUANTDINGER_BASE_URL": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_no_token_first_run(self):
        self.assertEqual(self.creds.current(), (connector.DEFAULT_BASE_URL, None))

    def test_normalized_and_rejected_endpoints(self):
        self.assertEqual(connector.normalize_base_url("https://EXAMPLE.com:443/"), "https://example.com")
        self.assertEqual(connector.normalize_base_url("http://[::1]:8888"), "http://[::1]:8888")
        for url in ("http://example.com", "https://u:p@example.com", "https://example.com/path",
                    "https://example.com?secret=x", "https://example.com#fragment", "https://example.com:bad", "file:///tmp"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                connector.normalize_base_url(url)

    def test_save_is_endpoint_bound_and_config_has_no_secret(self):
        self.creds.save(connector.DEFAULT_BASE_URL, TOKEN_A)
        self.assertEqual(self.creds.current()[1], TOKEN_A)
        path = self.root / "config.json"
        self.assertNotIn(TOKEN_A, path.read_text())
        changed = json.loads(path.read_text())
        changed["base_url"] = "https://other.example.com"
        path.write_text(json.dumps(changed))
        self.assertIsNone(self.creds.current()[1])

    def test_failed_atomic_save_preserves_previous(self):
        self.creds.save(connector.DEFAULT_BASE_URL, TOKEN_A)
        before = dict(self.vault.values)
        with patch.object(connector.os, "replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.creds.save(connector.DEFAULT_BASE_URL, TOKEN_B)
        self.assertEqual(self.vault.values, before)
        self.assertEqual(self.creds.current()[1], TOKEN_A)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_new_credentials_override_stale_environment(self):
        self.creds.save(connector.DEFAULT_BASE_URL, TOKEN_B)
        with patch.dict(os.environ, {"QUANTDINGER_AGENT_TOKEN": TOKEN_A, "QUANTDINGER_BASE_URL": "http://localhost:9999"}):
            self.assertEqual(self.creds.current(), (connector.DEFAULT_BASE_URL, TOKEN_B))

    def test_legacy_credential_remains_compatible(self):
        (self.root / "config.json").write_text(json.dumps({"base_url": connector.DEFAULT_BASE_URL}))
        self.vault.set_password(connector.SECRET_SERVICE, connector.SECRET_ACCOUNT, TOKEN_A)
        self.assertEqual(self.creds.current()[1], TOKEN_A)
        self.creds.save(connector.DEFAULT_BASE_URL, TOKEN_B)
        self.assertEqual(self.creds.current()[1], TOKEN_B)

    def test_redaction_in_nested_content(self):
        value = {"content": [{"text": "header " + TOKEN_A}], "result": {"echo": TOKEN_B}}
        self.assertNotIn("qd_agent_", json.dumps(connector.redact(value)))


class VerifyTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, status, body):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(status, json=body, headers={"Location": "https://untrusted.example.com"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
        with patch.object(connector.httpx, "AsyncClient", return_value=client):
            value = await connector.verify(connector.DEFAULT_BASE_URL, TOKEN_A)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url.path, "/api/agent/v1/whoami")
        return value

    async def test_valid_identity_allowlist_and_redaction(self):
        value = await self.check(200, {"data": {**IDENTITY, "agent_name": TOKEN_A, "token": TOKEN_A}})
        self.assertEqual(value["status"], "verified")
        self.assertNotIn(TOKEN_A, json.dumps(value))
        self.assertNotIn("token", value["identity"])

    async def test_rejected_tokens(self):
        for status in (401, 403):
            with self.subTest(status=status):
                value = await self.check(status, {"error": TOKEN_A})
                self.assertEqual(value["status"], "authentication_rejected")
                self.assertNotIn(TOKEN_A, json.dumps(value))

    async def test_redirect_not_followed(self):
        self.assertEqual((await self.check(302, {}))["status"], "service_unavailable")

    async def test_service_error_not_misdiagnosed_as_invalid_token(self):
        self.assertEqual((await self.check(503, {}))["status"], "service_unavailable")

    async def test_html_or_wrong_service_identity_rejected(self):
        self.assertEqual((await self.check(200, {"data": {"hello": "world"}}))["status"], "unexpected_identity_response")

    async def test_bad_format_never_contacts_service(self):
        with patch.object(connector.httpx, "AsyncClient") as client:
            self.assertEqual((await connector.verify(connector.DEFAULT_BASE_URL, "invalid"))["status"], "invalid_token_format")
            client.assert_not_called()

    async def test_timeout_and_network_failure(self):
        for exception, expected in ((httpx.ReadTimeout("fixture"), "verification_timeout"),
                                    (httpx.ConnectError("fixture"), "service_unreachable")):
            def handler(request):
                raise exception
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            with patch.object(connector.httpx, "AsyncClient", return_value=client):
                self.assertEqual((await connector.verify(connector.DEFAULT_BASE_URL, TOKEN_A))["status"], expected)

    async def test_storage_failure_does_not_claim_connected(self):
        with tempfile.TemporaryDirectory(prefix="qd-storage-test-") as directory:
            creds = connector.Credentials(Path(directory), MemoryVault())
            bridge = connector.Bridge(creds)
            with patch.object(connector, "verify", return_value={"status": "verified", "identity": IDENTITY}), patch.object(creds, "save", side_effect=OSError("fixture")):
                response = await bridge.connect({"agent_token": TOKEN_A, "base_url": connector.DEFAULT_BASE_URL})
            self.assertTrue(response.isError)
            self.assertEqual(data(response)["status"], "credential_storage_failed")

    async def test_failed_upstream_operation_is_not_replayed(self):
        calls = []

        @asynccontextmanager
        async def broken_upstream(endpoint, token):
            calls.append("opened")
            raise OSError("fixture_response_lost")
            yield

        with tempfile.TemporaryDirectory(prefix="qd-no-replay-test-") as directory:
            creds = connector.Credentials(Path(directory), MemoryVault())
            creds.save(connector.DEFAULT_BASE_URL, TOKEN_A)
            bridge = connector.Bridge(creds)
            bridge.catalog = {"fixture_write": connector.types.Tool(name="fixture_write", inputSchema={"type": "object"})}
            with patch.object(connector, "upstream", broken_upstream):
                response = await bridge.call_tool("fixture_write", {})
            self.assertTrue(response.isError)
            self.assertFalse(data(response)["automatically_retried"])
            self.assertTrue(data(response)["outcome_may_be_unknown"])
            self.assertEqual(calls, ["opened"])


class WindowsVaultTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows OS vault")
    def test_real_os_vault_round_trip_with_disposable_fake_token(self):
        service = "QuantDinger Connector Isolated Test " + uuid.uuid4().hex
        account = "generated-fixture-only"
        connector.keyring.set_password(service, account, TOKEN_A)
        try:
            self.assertEqual(connector.keyring.get_password(service, account), TOKEN_A)
        finally:
            connector.keyring.delete_password(service, account)


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        identity = getattr(self.server, "identities", {TOKEN_A: 101, TOKEN_B: 202}).get(token)
        self.server.requests.append((self.command, self.path, identity))
        if self.path == "/api/agent/v1/health":
            status, body = 200, {"data": {"ok": True}}
        elif not identity:
            status, body = 401, {"error": "Unknown agent token"}
        elif self.path == "/api/agent/v1/whoami":
            status, body = 200, {"data": {**IDENTITY, "user_id": identity}}
        elif self.path == "/api/agent/v1/markets":
            status, body = 200, {"data": {"markets": ["Crypto"], "fixture_identity": identity, "echo": token}}
        else:
            status, body = 404, {"error": "fixture_route_not_found"}
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@asynccontextmanager
async def fixture_session(root, endpoint):
    parameters = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve()), "--worker", str(root)],
        env={"QUANTDINGER_AGENT_TOKEN": "", "QUANTDINGER_BASE_URL": endpoint})
    with (root / "stderr.log").open("a") as errors:
        async with stdio_client(parameters, errlog=errors) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                initialized = await session.initialize()
                assert initialized.serverInfo.version == connector.package_version("quantdinger-mcp")
                yield session


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_environment_switch_requires_target_token_and_preserves_previous_on_failure(self):
        servers = []
        for identities in ({TOKEN_A: 101}, {TOKEN_B: 202}):
            server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
            server.requests = []
            server.identities = identities
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            servers.append(server)
        endpoints = [f"http://127.0.0.1:{server.server_port}" for server in servers]
        with tempfile.TemporaryDirectory(prefix="qd-environment-test-") as directory:
            async with fixture_session(Path(directory), endpoints[0]) as session:
                self.assertEqual(data(await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_A}))["status"], "connected")
                rejected = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_A, "base_url": endpoints[1]})
                self.assertTrue(rejected.isError)
                self.assertEqual(data(await session.call_tool("connection_status", {}))["base_url"], endpoints[0])
                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 101)
                switched = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_B, "base_url": endpoints[1]})
                self.assertEqual(data(switched)["base_url"], endpoints[1])
                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
        self.assertEqual(len(servers[0].requests), 2)
        self.assertEqual(len(servers[1].requests), 3)

    async def test_packaged_windows_launcher_discovers_tools_without_loading_credentials(self):
        if os.name != "nt":
            self.skipTest("Windows launcher")
        plugin = Path(__file__).resolve().parents[1]
        definition = json.loads((plugin / ".mcp.json").read_text())["mcpServers"]["quantdinger"]
        parameters = StdioServerParameters(command=definition["command"], args=definition["args"], cwd=str(plugin))
        with tempfile.TemporaryFile(mode="w+") as errors:
            async with stdio_client(parameters, errlog=errors) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                    await session.initialize()
                    names = {tool.name for tool in (await session.list_tools()).tools}
                    self.assertIn("connect_quantdinger", names)
                    self.assertIn("submit_backtest", names)
            errors.seek(0)
            self.assertNotIn("Traceback", errors.read())

    async def test_same_mcp_session_first_connect_reject_rotate_and_resume(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        endpoint = f"http://127.0.0.1:{server.server_port}"
        with tempfile.TemporaryDirectory(prefix="qd-protocol-test-") as directory:
            root = Path(directory)
            async with fixture_session(root, endpoint) as session:
                listed = await session.list_tools()
                names = {t.name for t in listed.tools}
                self.assertTrue({"connect_quantdinger", "connection_status", "whoami", "submit_backtest", "list_markets"} <= names)
                async with connector.upstream(connector.DEFAULT_BASE_URL, "not-configured") as original:
                    original_tools = (await original.list_tools()).tools
                by_name = {t.name: t for t in listed.tools}
                for tool in original_tools:
                    self.assertEqual(by_name[tool.name].model_dump(), tool.model_dump())
                self.assertEqual(len(names), len(original_tools) + 2)
                self.assertEqual(server.requests, [])
                self.assertEqual(data(await session.call_tool("connection_status", {}))["status"], "not_connected")
                missing = await session.call_tool("whoami", {})
                self.assertTrue(missing.isError)
                self.assertEqual(data(missing)["status"], "not_connected")
                bad = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_BAD})
                self.assertTrue(bad.isError)
                self.assertFalse((root / "config.json").exists())
                first = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_A})
                self.assertEqual(data(first)["status"], "connected")
                self.assertFalse(data(first)["restart_required"])
                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 101)
                rejected = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_BAD})
                self.assertTrue(data(rejected)["previous_connection_preserved"])
                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 101)
                rotated = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_B})
                self.assertEqual(data(rotated)["identity"]["user_id"], 202)
                self.assertEqual(data(await session.call_tool("whoami", {}))["user_id"], 202)
                resumed = await session.call_tool("list_markets", {})
                self.assertEqual(data(resumed)["fixture_identity"], 202)
                self.assertNotIn(TOKEN_B, resumed.model_dump_json())
                invalid_schema = await session.call_tool("connect_quantdinger", {"agent_token": {"secret": TOKEN_A}})
                self.assertTrue(invalid_schema.isError)
                self.assertNotIn(TOKEN_A, invalid_schema.model_dump_json())
                forbidden = await session.call_tool("connect_quantdinger", {"agent_token": TOKEN_A, "base_url": "http://non-loopback.example"})
                self.assertTrue(forbidden.isError)
            async with fixture_session(root, endpoint) as reloaded:
                self.assertEqual(data(await reloaded.call_tool("whoami", {}))["user_id"], 202)
            for token in (TOKEN_A, TOKEN_B, TOKEN_BAD):
                self.assertNotIn(token, (root / "config.json").read_text())
                self.assertNotIn(token, (root / "stderr.log").read_text())
            self.assertTrue(all(method == "GET" for method, _, _ in server.requests))
            self.assertEqual(len(server.requests), 9)
            print(f"Protocol verified: {len(original_tools)} original tools + 2 connector tools; same-session A -> B; upstream {importlib.metadata.version('quantdinger-mcp')}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        root = Path(sys.argv[2])
        asyncio.run(connector.Bridge(connector.Credentials(root, FixtureVault(root))).run())
    else:
        unittest.main(verbosity=2)

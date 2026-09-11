"""Stable MCP bridge with verified, hot-swappable QuantDinger credentials."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import getpass
import hashlib
from importlib.metadata import version as package_version
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse
import uuid

import httpx
import jsonschema
import keyring
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


DEFAULT_BASE_URL = "https://ai.quantdinger.com"
MCP_REQUIREMENT = "quantdinger-mcp>=0.6,<0.7"
SECRET_SERVICE = "QuantDinger Connector"
SECRET_ACCOUNT = "agent-token"
TOKEN_PATTERN = re.compile(r"qd_agent_[A-Za-z0-9_-]{8,512}\Z")


def connector_root() -> Path:
    raw = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    return Path(raw or Path.home() / ".config") / "QuantDinger" / "Connector"


def normalize_base_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlparse(raw)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.path not in {"", "/"} or parsed.username or parsed.password
            or parsed.query or parsed.fragment or any(c.isspace() for c in raw)):
        raise ValueError("invalid_endpoint")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("https_required")
    port = parsed.port
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if port and port != {"http": 80, "https": 443}[parsed.scheme]:
        host += f":{port}"
    return f"{parsed.scheme}://{host}"


def redact(value, token: str | None = None):
    if isinstance(value, str):
        if token:
            value = value.replace(token, "[REDACTED]")
        return re.sub(r"qd_agent_[A-Za-z0-9_-]+", "[REDACTED]", value)
    if isinstance(value, dict):
        return {redact(k, token): redact(v, token) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, token) for v in value]
    return value


def result(data: dict, error: bool = False) -> types.CallToolResult:
    safe = redact(data)
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(safe))],
                                structuredContent=safe, isError=error)


class Credentials:
    def __init__(self, root: Path | None = None, store=None):
        self.root = root or connector_root()
        self.store = store or keyring

    def config(self) -> dict:
        path = self.root / "config.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            data = {"base_url": os.environ.get("QUANTDINGER_BASE_URL") or DEFAULT_BASE_URL}
        data["base_url"] = normalize_base_url(data.get("base_url") or DEFAULT_BASE_URL)
        return data

    def current(self) -> tuple[str, str | None]:
        data = self.config()
        endpoint = data["base_url"]
        account = data.get("credential_account")
        if account:
            digest = hashlib.sha256(endpoint.encode()).hexdigest()[:24]
            if not account.startswith(f"endpoint:{digest}:"):
                return endpoint, None
            return endpoint, self.store.get_password(SECRET_SERVICE, account)
        # Only legacy installations consult inherited environment credentials.
        env_endpoint = normalize_base_url(os.environ.get("QUANTDINGER_BASE_URL") or endpoint)
        token = os.environ.get("QUANTDINGER_AGENT_TOKEN") if env_endpoint == endpoint else None
        legacy = self.store.get_password(SECRET_SERVICE, SECRET_ACCOUNT) if (self.root / "config.json").exists() else None
        return endpoint, token or legacy

    def save(self, endpoint: str, token: str) -> None:
        digest = hashlib.sha256(endpoint.encode()).hexdigest()[:24]
        account = f"endpoint:{digest}:{uuid.uuid4().hex}"
        self.root.mkdir(parents=True, exist_ok=True)
        self.store.set_password(SECRET_SERVICE, account, token)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.root,
                                             prefix="config-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump({"base_url": endpoint, "credential_account": account}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.root / "config.json")
        except Exception:
            try:
                self.store.delete_password(SECRET_SERVICE, account)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            raise
        # Old credential revisions remain in the OS vault for in-flight sessions.


async def verify(endpoint: str, token: str) -> dict:
    if not TOKEN_PATTERN.fullmatch(token):
        return {"status": "invalid_token_format"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.get(endpoint + "/api/agent/v1/whoami",
                                        headers={"Authorization": "Bearer " + token})
        if response.status_code in {401, 403}:
            return {"status": "authentication_rejected", "http_status": response.status_code}
        if response.status_code != 200:
            return {"status": "service_unavailable", "http_status": response.status_code}
        body = response.json()
        identity = body.get("data", body) if isinstance(body, dict) else None
        if (not isinstance(identity, dict) or identity.get("user_id") is None
                or not isinstance(identity.get("scopes"), list)
                or not isinstance(identity.get("paper_only"), bool)):
            return {"status": "unexpected_identity_response"}
        fields = ("user_id", "agent_name", "scopes", "markets", "instruments", "paper_only",
                  "rate_limit_per_min", "max_order_notional", "max_daily_notional")
        return {"status": "verified", "identity": redact({k: identity[k] for k in fields if k in identity}, token)}
    except httpx.TimeoutException:
        return {"status": "verification_timeout"}
    except httpx.RequestError:
        return {"status": "service_unreachable"}
    except (ValueError, TypeError):
        return {"status": "unexpected_identity_response"}


@asynccontextmanager
async def upstream(endpoint: str, token: str):
    params = StdioServerParameters(command=sys.executable, args=["-m", "quantdinger_mcp.server"],
                                  env={"QUANTDINGER_BASE_URL": endpoint,
                                       "QUANTDINGER_AGENT_TOKEN": token,
                                       "QUANTDINGER_MCP_TRANSPORT": "stdio"})
    # Upstream exception logs may contain request headers; do not forward them.
    with open(os.devnull, "w") as errors:
        async with stdio_client(params, errlog=errors) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=360)) as session:
                await session.initialize()
                yield session


class Bridge:
    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials or Credentials()
        self.lock = asyncio.Lock()
        self.catalog = None
        metadata = json.loads(Path(__file__).with_name("connector-tools.json").read_text(encoding="utf-8"))
        self.local_tools = [types.Tool.model_validate(t) for t in metadata["tools"]]
        self.server = Server("quantdinger", version=package_version("quantdinger-mcp"), instructions=metadata["instructions"])
        self.server.list_tools()(self.list_tools)
        # Custom validation avoids reflecting a submitted secret in schema errors.
        self.server.call_tool(validate_input=False)(self.call_tool)

    async def list_tools(self) -> list[types.Tool]:
        if self.catalog is None:
            # Discovery does not call HTTP or load a user's credential.
            async with upstream(DEFAULT_BASE_URL, "not-configured") as session:
                tools = []
                cursor = None
                while True:
                    page = await session.list_tools(cursor=cursor)
                    tools.extend(page.tools)
                    cursor = page.nextCursor
                    if not cursor:
                        break
                self.catalog = {t.name: t for t in tools}
        return self.local_tools + list(self.catalog.values())

    async def connect(self, arguments: dict) -> types.CallToolResult:
        endpoint = normalize_base_url(arguments.get("base_url") or self.credentials.config()["base_url"])
        token = arguments["agent_token"].strip()
        checked = await verify(endpoint, token)
        if checked["status"] != "verified":
            return result({**checked, "base_url": endpoint, "previous_connection_preserved": True}, True)
        try:
            self.credentials.save(endpoint, token)
        except Exception:
            return result({"status": "credential_storage_failed", "previous_connection_preserved": True}, True)
        return result({"status": "connected", "base_url": endpoint, "restart_required": False,
                       "identity": checked["identity"], "credential_storage": "os_keyring",
                       "chat_history_contains_token": True})

    async def call_tool(self, name: str, arguments: dict) -> types.CallToolResult:
        try:
            async with self.lock:
                definitions = {t.name: t for t in self.local_tools}
                if name not in definitions:
                    definitions.update({t.name: t for t in await self.list_tools()})
                if name not in definitions:
                    return result({"status": "unknown_tool"}, True)
                try:
                    jsonschema.validate(arguments, definitions[name].inputSchema)
                except jsonschema.ValidationError:
                    return result({"status": "invalid_arguments", "tool": name}, True)
                if name == "connect_quantdinger":
                    return await self.connect(arguments)
                endpoint, token = self.credentials.current()
                if name == "connection_status":
                    return result({"status": "configured" if token else "not_connected", "base_url": endpoint,
                                   "credential_present": bool(token), "identity_verified_now": False,
                                   "restart_required": False})
                if not token and name != "check_health":
                    return result({"status": "not_connected", "base_url": endpoint,
                                   "next_tool": "connect_quantdinger"}, True)
                # Each operation snapshots current credentials. No stale child survives rotation.
                async with upstream(endpoint, token or "not-configured") as session:
                    forwarded = await session.call_tool(name, arguments)
                return types.CallToolResult.model_validate(redact(forwarded.model_dump(mode="json"), token))
        except ValueError:
            return result({"status": "invalid_configuration_or_endpoint"}, True)
        except Exception:
            # Never replay a failed operation: a write may already have reached the service.
            return result({"status": "connector_operation_failed", "automatically_retried": False,
                           "outcome_may_be_unknown": name not in {"connect_quantdinger", "connection_status"}}, True)

    async def run(self):
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())


def main() -> int:
    parser = argparse.ArgumentParser(prog="quantdinger-connector")
    commands = parser.add_subparsers(dest="command")
    config = commands.add_parser("configure")
    config.add_argument("--base-url")
    config.add_argument("--token-stdin", action="store_true")
    commands.add_parser("status")
    commands.add_parser("update")
    args = parser.parse_args()
    bridge = Bridge()
    if args.command == "configure":
        token = sys.stdin.readline().strip() if args.token_stdin else getpass.getpass("Agent Token: ").strip()
        values = {"agent_token": token}
        if args.base_url:
            values["base_url"] = args.base_url
        response = asyncio.run(bridge.connect(values))
        print(json.dumps(response.structuredContent))
        return int(response.isError)
    if args.command == "status":
        endpoint, token = bridge.credentials.current()
        print(json.dumps({"configured": bool(token), "base_url": endpoint, "mcp_requirement": MCP_REQUIREMENT}))
        return 0
    if args.command == "update":
        print(json.dumps({"status": "update_plugin_runtime_bundle", "in_place_pip_update_supported": False}))
        return 2
    asyncio.run(bridge.run())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("connector_startup_failed", file=sys.stderr)
        raise SystemExit(2) from None

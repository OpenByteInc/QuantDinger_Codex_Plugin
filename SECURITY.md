# Security and data handling

Report vulnerabilities privately to **support@quantdinger.com**. Do not include a live token, exchange key, password or private account export in a public issue. This contact comes from the plugin's publisher metadata; no response-time commitment is implied.

## Credentials and boundaries

- Each user supplies a scoped QuantDinger Agent Token. No real credentials are shipped.
- The connector validates a replacement before storing it in the OS credential vault. Non-secret endpoint settings and a credential reference are stored separately.
- The chat-based connection flow places the token in conversation/tool history. Use the masked `configure` terminal prompt if you want to avoid that exposure.
- Tokens are bound to the selected endpoint. A failed replacement preserves the previous local connection.
- Connection settings are shared by plugin tasks for the same OS user. A running request keeps the credential snapshot with which it started.
- Revocation, permissions, paper-only enforcement, account ownership and charges are controlled by the QuantDinger backend. Risk annotations do not replace those controls.

## Local files and network traffic

On Windows, runtime caches and non-secret connection settings live under `%LOCALAPPDATA%\QuantDinger\Connector`. On Mac they live under `~/Library/Application Support/QuantDinger/Connector`. Credentials use the `QuantDinger Connector` service in Windows Credential Manager or macOS Keychain. Older credential revisions and runtime directories may remain after upgrades or plugin removal.

Tools send the requested market queries, strategy source, account queries or authorized operations to the selected QuantDinger endpoint. Tool results are returned to the Codex conversation. Hosted-service data handling and charges are separate from this open-source license; consult the operator of the selected endpoint.

Uninstalling a local plugin does not revoke its token or stop a server-side strategy. Revoke unused tokens in QuantDinger. Confirm which other local tasks use the shared connection before removing local settings or vault entries.

## Artifact integrity

The runtime manifest pins the archive hash, and the installer verifies the packaged inventory. These checks detect corruption relative to the checked-out manifest; they do not prove publisher identity if both files have been replaced. Review the source, use a trusted repository/ref, and do not bypass failed checks.

Mac setup uses uv-managed Python and exact dependency versions with wheel hashes from PyPI. First launch requires network access. Subsequent launches validate environment versions and imports, but do not hash every installed file. The managed Python distribution is resolved by uv; its patch version is not pinned by this repository. Protect local filesystem access and use an official uv installation.

The tests use local HTTP fixtures and generated dummy tokens. Never replace those values with production secrets. macOS CI uses disposable keychains on ephemeral runners; users keep their normal login Keychain protections.

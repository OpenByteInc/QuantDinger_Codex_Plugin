# Install → connect → run your first backtest

[English](INSTALL.md) · [简体中文](INSTALL.zh-CN.md) · [Back to overview](../README.md)

## Before you begin

You need a QuantDinger account, Git, and a Codex client with plugin support. In PowerShell on Windows or Terminal on Mac, check:

```text
git --version
codex --version
codex plugin --help
```

If a command is missing, install [Git](https://git-scm.com/downloads) or the [Codex CLI](https://developers.openai.com/codex/cli), then reopen your terminal. Use the same OS account and Codex profile for the CLI installation and the desktop app. A custom `CODEX_HOME` profile is separate from the default profile.

## Install on Windows

Windows 10/11 x64. Paste these commands into **PowerShell**:

```powershell
codex plugin marketplace add OpenByteInc/quantdinger-codex-plugin
codex plugin add quantdinger@quantdinger
```

The plugin includes Python and its dependencies. First launch checks the archive and extracts a private runtime; no system Python, pip or API-key environment variable is needed.

## Install on Mac

Open **Terminal**. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If you already use Homebrew, `brew install uv` is an alternative. You only need one installation method. The launcher checks the standard uv and Homebrew locations as well as `PATH`.

```bash
codex plugin marketplace add OpenByteInc/quantdinger-codex-plugin
codex plugin add quantdinger-macos@quantdinger
```

Choose **QuantDinger for Mac**, not the Windows entry. The launcher supports Apple Silicon (`arm64`) and Intel (`x86_64`); your chosen Codex client must also support that hardware. This is a Mac desktop/CLI integration, not an iOS app.

On first launch, stay online while uv downloads a managed Python 3.13 and installs the exact, hash-locked dependencies into a private environment. This can take several minutes. Subsequent launches reuse the environment; market queries still need network access.

## Open the plugin

Open a **new task** in Codex, type `@`, and select **QuantDinger** on Windows or **QuantDinger for Mac**. Alternatively, open the plugin details and click **Try now** or one of its example prompts.

![Real plugin details showing Try now and example prompts](assets/codex-plugin-screen.png)

<sub>Maintainer-provided Windows capture, before the 0.2.0 title and Mac entry. The product controls belong to Codex and may look different in your version.</sub>

The first useful check is:

```text
Check my QuantDinger connection status. If I am connected, verify my
endpoint and permissions. Do not create a strategy or place an order.
```

An unconfigured account is normal on first use. A missing tool or failed runtime startup is an installation issue, not proof of a bad token.

## Connect your account

1. Sign in to [QuantDinger](https://ai.quantdinger.com).
2. Open **[Profile → Agent Tokens](https://ai.quantdinger.com/#/profile?tab=agentTokens)** and create a scoped, revocable token. Start with paper-only permissions.
3. Ask Codex to connect your QuantDinger account and supply the token when prompted.
4. Look for **`connected`**, the expected endpoint, permissions and paper-only status. Continue in the same task.

The connector verifies credentials before saving them. Installing or connecting does not start a trading strategy. A failed replacement preserves the previous stored connection, so resolve the failure before continuing under a different account.

Local tokens use Windows Credential Manager or macOS Keychain. On Mac, allow a Keychain request only after checking it belongs to the Python runtime you just installed. The plugin does not store the token in a plaintext configuration file. A token supplied in chat still appears in conversation/tool history.

### Keep your token out of chat

Use a local checkout and the masked terminal prompt instead:

```text
git clone https://github.com/OpenByteInc/quantdinger-codex-plugin.git
cd quantdinger-codex-plugin
```

Windows, PowerShell:

```powershell
.\plugins\quantdinger\scripts\launch-quantdinger.cmd configure
```

Mac, Terminal:

```bash
/bin/bash plugins/quantdinger-macos/scripts/launch-quantdinger.sh configure
```

Paste the token into the hidden prompt. The checkout and installed plugin share the same OS-user connection store. Return to Codex and ask it to verify the connection. Do not put a token directly in a shell command, screenshot or issue.

### Self-hosted QuantDinger

Ask Codex to connect to your **explicit backend root URL**, using a token issued by that instance. Or append `--base-url https://your-quantdinger.example` to the `configure` command above. Replace the example with your own root URL; do not append `/mcp` or an API path. HTTPS is required except for loopback addresses such as `http://127.0.0.1:5000`.

Switching endpoints requires a token from the selected environment. The local plugin is a stdio MCP adapter; you do not need to operate a separate public MCP endpoint.

## Run a backtest you can find again

```text
Build an NVDA MA20/MA60 crossover strategy and backtest the last 90 days.
Use 10,000 initial capital, 0.1% fees and 0.05% slippage.
Save the result and return its runId, actual data dates, return,
maximum drawdown, completed trades and any remaining position.
Do not deploy or start trading.
```

Codex should compile/save the strategy and wait for the backtest job to complete. A submitted job is not a completed result. Use the returned **`runId`** to identify the standard record in QuantDinger's backtest history. If the tool reports a failure, ask for the failing stage and error rather than treating an estimate as a saved result.

Compare actual returned dates and costs. The backend intentionally may exclude the latest day to avoid timezone/provider availability failures. A strategy can legitimately finish with an open position or no completed trades. Ask for both fills and completed trades.

Try Hong Kong stocks (`0700.HK`), ETFs (`SPY`) or crypto (`BTC/USDT`) next. Availability follows the connected backend and data provider. Hosted operations may consume QuantDinger credits; Codex usage is separate. Research is assembled by the assistant from available tools, not a separate native AI-report tool.

## Update, local install and uninstall

To update the GitHub marketplace, run:

```text
codex plugin marketplace upgrade quantdinger
```

Then repeat your platform's `codex plugin add` command and open a new task. Keep only the entry appropriate for that machine enabled.

For a local checkout or an extracted source archive, open its root directory (the one containing `.agents/plugins/marketplace.json`), run `codex plugin marketplace add .`, then run the same platform-specific add command. If that marketplace name is already registered from GitHub, use the existing source or remove the old marketplace registration before switching; do not register two sources with the same name.

To uninstall, run **one** of:

```text
codex plugin remove quantdinger@quantdinger
codex plugin remove quantdinger-macos@quantdinger
```

Uninstalling does **not** revoke a token, delete the shared credential store or stop backend strategies. Revoke unused tokens in QuantDinger. Stop strategies only when you intend to stop them.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `codex` or `plugin` command missing | Install/update the Codex CLI, reopen the terminal, and confirm the client supports plugins. |
| Installed but absent from the app | Match OS user/profile, open a new task, and confirm the marketplace and platform entry. Restart the app if it has not refreshed. |
| Mac tries to run `cmd.exe` | Remove the Windows entry and install `quantdinger-macos@quantdinger`. |
| `uv_required` | Install uv using the official instructions above. The launcher searches standard per-user and Homebrew paths. |
| First Mac setup times out | Check access to Python distribution downloads and PyPI, then retry. Completed environments are reused; a partial environment is quarantined before retry. |
| Credential storage fails on Mac | Unlock your login Keychain and check the relevant access prompt. Do not disable Keychain protection. |
| Authentication rejected | Check the selected endpoint, token validity and revocation. Do not confuse an unreachable server with rejected credentials. |
| Tool denied or insufficient credits | Check backend permissions, paper-only restrictions and balance. Reinstalling cannot grant permissions or credits. |
| Backtest missing from history | Confirm completion and a returned `runId`, then check that the UI uses the same account and endpoint. |

Runtime caches and non-secret connection settings live at:

- Windows: `%LOCALAPPDATA%\QuantDinger\Connector`
- Mac: `~/Library/Application Support/QuantDinger/Connector`

When opening an [issue](https://github.com/OpenByteInc/quantdinger-codex-plugin/issues), include OS/architecture, Codex version, plugin version, the failing step and redacted error text. Never attach tokens, credential stores or private account exports.

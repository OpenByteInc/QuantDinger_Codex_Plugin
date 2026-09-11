<p align="center">
  <img src="plugins/quantdinger/assets/quantdinger-cat-logo.png" width="96" alt="QuantDinger logo" />
</p>

# QuantDinger for Codex

**Turn a trading idea into a strategy you can test.**

[English](README.md) · [简体中文](README.zh-CN.md) · [Website](https://www.quantdinger.com) · [Open QuantDinger](https://ai.quantdinger.com) · [Backend & MCP source](https://github.com/OpenByteInc/QuantDinger)

Research **US stocks, Hong Kong stocks, ETFs, and crypto** from a Codex conversation. Build strategy code, run historical backtests with costs, compare results, and inspect your QuantDinger accounts and trading activity.

This repository distributes the QuantDinger plugin through a **GitHub marketplace**. Users add this source and install the plugin themselves. It is not a listing in OpenAI's public plugin directory or an OpenAI endorsement.

![Illustrative strategy-to-backtest workflow](plugins/quantdinger/assets/strategy-workflow.png)

*Illustration only; displayed results are not a performance claim.*

## What you can do

| Workflow | What you get |
| --- | --- |
| Explore markets | Symbol search, available quotes, historical prices, volume, factors and universes |
| Build a strategy | Strategy API V2 authoring guidance, compilation, saved source and version history |
| Backtest and compare | Asynchronous backtests, saved `runId`, returns, drawdowns, costs and trade records |
| Inspect trading | Account snapshots, strategy positions, fills, pending orders and runtime state |
| Operate with permission | Supported paper/live actions subject to your token scopes, account settings and explicit confirmation |

The AI assistant combines the available tools to research and explain results. This release does not expose a separate native QuantDinger AI research-report generator. Markets, data freshness and broker actions depend on the connected backend and providers.

## Platform status

| Platform | Status |
| --- | --- |
| Windows 10/11 x64 | Bundled runtime; connector and offline installation regression tests included |
| macOS, Apple Silicon | Planned; the current Windows package does not run on Mac |
| Other architectures / Linux | No packaged runtime in this release |

Plugin **0.1.0** bundles **quantdinger-mcp 0.6.2** and Python **3.13.15**. Plugin and MCP versions are separate. The Windows runtime includes its dependencies, so users do not need to install Python or pip. Clean-machine compatibility still depends on Windows security settings and the Codex client version.

## Install on Windows

You need a supported Codex client with plugin support, the `codex` command available in your terminal, Git, and a QuantDinger account or self-hosted instance. Managed workspaces may restrict custom plugin sources.

Run in PowerShell:

```powershell
codex plugin marketplace add OpenByteInc/quantdinger-codex-plugin
codex plugin add quantdinger@quantdinger
```

Open a new Codex task and select **QuantDinger** with `@`. If your client has a plugin browser, look for the QuantDinger source there. Update Codex if `plugin` or `marketplace` is not a recognized command.

The Git repository includes the approximately 26 MB Windows runtime archive so a normal marketplace install is complete. First launch verifies and extracts it locally; no Python download or online dependency installation happens during bootstrap. Market queries and account operations still require a connection to your QuantDinger service.

### Install from a local checkout

```powershell
git clone https://github.com/OpenByteInc/quantdinger-codex-plugin.git
cd quantdinger-codex-plugin
codex plugin marketplace add .
codex plugin add quantdinger@quantdinger
```

Keep the checkout in place when using it as a local marketplace. Unzipping a repository by itself does not install the plugin; add the extracted repository root as a marketplace first. See the [official packaging guide](https://developers.openai.com/plugins/build/plugins) for client-specific behavior.

## Connect your account

1. Open [QuantDinger's Agent Token settings](https://ai.quantdinger.com/#/profile?tab=agentTokens) and issue a scoped, revocable token. Start with paper-only permissions for testing.
2. In a QuantDinger-enabled Codex task, ask to connect your account, then supply the token when prompted. **A token entered in a conversation is present in chat/tool history.** The connector verifies it with the selected QuantDinger endpoint and stores its local copy in the OS credential vault; it does not echo the token in its response.
3. Check the reported endpoint, permissions and paper-only status, then ask for your first analysis or backtest. Connecting an account does not authorize a trade.

Default backend: `https://ai.quantdinger.com`. For a self-hosted instance, explicitly specify its root URL and use a token issued by that instance. HTTPS is required except for loopback development addresses.

Prefer not to put a token in chat? From the repository root, configure it through the masked terminal prompt instead:

```powershell
.\plugins\quantdinger\scripts\launch-quantdinger.cmd configure
```

For self-hosting, append `--base-url https://your-quantdinger-host.example`. Never put the token itself on a command line, in a Git commit, or in a GitHub issue.

## Try these prompts

**US stocks — build and backtest**

> Build an NVDA MA20/MA60 crossover strategy for the last 90 days. Use 10,000 initial capital, 0.1% fees and 0.05% slippage. Save the backtest and return its runId, drawdown and completed trades.

**Hong Kong — understand the market**

> Analyze Tencent (0700.HK) over the last 90 days. Explain the trend, volume changes and historical drawdown. Show the actual dates covered by the data.

**ETFs — compare strategies**

> Compare moving-average and RSI strategies on SPY using the same dates, capital and costs. Explain why their results differ.

**Crypto — test more complete rules**

> Build a BTC/USDT strategy with a trend filter, RSI entry, a 2% stop loss, a 3% take profit and a maximum holding period. Backtest it and inspect completed trades and any remaining position.

**Account monitoring — read only**

> Show my paper-account positions, strategy trades and pending orders. Explain anything that needs attention without changing the account.

Historical data may conservatively exclude the latest day to avoid timezone and provider availability failures. Use the returned data range when interpreting or comparing results. A strategy can legitimately produce no closed trades over a given period.

## Architecture and charges

```text
Codex on your computer
  -> local QuantDinger Connector (MCP over stdio)
  -> pinned quantdinger-mcp service
  -> your QuantDinger backend (HTTPS Agent Gateway)
```

Each OS user connects their own account. Connection settings are shared across that user's plugin tasks; switching credentials affects subsequent calls. The backend enforces permissions, account isolation, idempotency and billing. There is no shared administrator token in this repository.

The plugin source is open source. Hosted QuantDinger operations may consume credits according to the service's current pricing; open-source installation does not make cloud usage free. Codex access and usage are separate.

## Update and uninstall

For the GitHub marketplace installation:

```powershell
codex plugin marketplace upgrade quantdinger
codex plugin add quantdinger@quantdinger
```

Start a new task after a plugin update. Ordinary token replacement does not require restarting Codex. Maintainers ship complete tested runtime bundles; the connector does not run an in-place pip upgrade on customers' machines.

To remove the plugin:

```powershell
codex plugin remove quantdinger@quantdinger
```

Uninstalling the plugin does **not** stop strategies already running on your QuantDinger backend or revoke its Agent Token. Manage those separately in QuantDinger. Local runtime caches and credential-vault entries may remain; see [security and data handling](SECURITY.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Plugin not visible | Marketplace was added, plugin installed, and a new task opened; check workspace policy and Codex version |
| `cmd.exe` unavailable / unsupported platform | This package is Windows x64; macOS packaging is still planned |
| First launch fails | Runtime archive integrity, write access to local app data, Windows security policy; do not disable integrity checks |
| Authentication rejected | Correct backend and a valid, unexpired token with the required scopes |
| Insufficient credits | QuantDinger balance and the operation's current price |
| No complete backtest trades | Check entry/exit rules, actual data range and open positions; inspect the saved run rather than assuming an execution bug |
| Account or order request denied | Token scopes, paper-only restrictions, provider environment and explicit action confirmation |

For reproducible problems, open an [issue](https://github.com/OpenByteInc/quantdinger-codex-plugin/issues) with OS, Codex/plugin versions and redacted error text. Do not attach credentials or private account records.

## Development and license

- [Build and test](BUILDING.md)
- [Contributing](CONTRIBUTING.md)
- [Security and data handling](SECURITY.md)
- [Changelog](CHANGELOG.md)

The marketplace catalog is in `.agents/plugins/marketplace.json`; the installable plugin is in `plugins/quantdinger/`. MCP business tools remain in the [main repository](https://github.com/OpenByteInc/QuantDinger/tree/main/mcp_server) and are consumed as a pinned PyPI release.

Licensed under [Apache-2.0](LICENSE). Bundled third-party software retains its own licenses; see [NOTICE](NOTICE). The license does not grant rights to use QuantDinger or OpenAI trademarks as an endorsement. Trading involves risk, and historical backtests do not guarantee future performance.

# QuantDinger plugin

Research US stocks, Hong Kong stocks, ETFs and crypto; build strategies, run backtests and inspect trading activity from Codex.

This folder is the installable Windows x64 plugin, version 0.2.0. It includes quantdinger-mcp 0.6.2, Python 3.13.15, a credential connector and four workflow skills. Mac users should install `quantdinger-macos@quantdinger` from the same marketplace.

- [English installation and usage guide](https://github.com/OpenByteInc/quantdinger-codex-plugin#readme)
- [简体中文安装与使用说明](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/README.zh-CN.md)
- [Build the runtime](BUILDING.md)
- [Security and credential handling](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/SECURITY.md)

Default backend: `https://ai.quantdinger.com`. Supply your own scoped Agent Token through the connection tool, or run `scripts/launch-quantdinger.cmd configure` for a masked terminal prompt. Tokens supplied in chat are present in conversation/tool history; the connector stores its local copy in the OS credential vault.

The first launch verifies and extracts the bundled runtime. No system Python or pip is required. Cloud operations need network access and may consume QuantDinger credits. Connecting or installing does not authorize a trade. Uninstalling does not stop strategies already running on the backend.

This is a GitHub-distributed plugin, not an OpenAI public-directory listing. Historical results do not guarantee future performance. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

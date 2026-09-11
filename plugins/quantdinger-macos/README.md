# QuantDinger for Mac

Research US stocks, Hong Kong stocks, ETFs and crypto from Codex. Build strategies, save backtests and inspect your QuantDinger accounts.

This is the macOS entry, version 0.2.0, with quantdinger-mcp 0.6.2 and four workflow skills. It supports Apple Silicon (M-series) Macs. Intel Macs are not supported in this release.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then:

```bash
codex plugin marketplace add OpenByteInc/quantdinger-codex-plugin
codex plugin add quantdinger-macos@quantdinger
```

First launch downloads managed Python 3.13 and hash-locked dependencies into `~/Library/Application Support/QuantDinger/Connector/runtimes`. Later launches reuse the isolated environment. Tokens use macOS Keychain. To avoid entering a token in chat, run `/bin/bash scripts/launch-quantdinger.sh configure` from this folder for a masked prompt.

- [English installation guide](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/docs/INSTALL.md)
- [简体中文安装指南](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/docs/INSTALL.zh-CN.md)
- [Build and tests](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/BUILDING.md)
- [Security](https://github.com/OpenByteInc/quantdinger-codex-plugin/blob/main/SECURITY.md)

Default backend: `https://ai.quantdinger.com`. Use your own scoped Agent Token. Connecting does not authorize trading; hosted operations may consume credits. Uninstalling does not revoke tokens or stop backend strategies. This is GitHub distribution, separate from OpenAI's public directory. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

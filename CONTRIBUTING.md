# Contributing

Use issues for reproducible bugs and scoped feature proposals. Include platform, Codex version, plugin version, expected behavior, actual behavior and redacted diagnostics. Never include real credentials or private financial records.

1. Fork the repository and create a branch.
2. Keep English source comments and update both README languages when user behavior changes.
3. Keep MCP business logic in the upstream QuantDinger repository. Update the pinned package and wheel lock here only after that release is available and tested.
4. Run the checks in [BUILDING.md](BUILDING.md).
5. Explain the user-visible change, validation and remaining platform limits in your pull request.

macOS work should include an appropriate launcher, isolated runtime setup, Keychain integration and tests on actual macOS runners. Do not advertise Mac support based only on Windows tests or a Python import check.

Do not commit personal configuration, local Codex caches, backend exports, logs or account-specific test reports. Code contributions are distributed under the repository's Apache-2.0 license.

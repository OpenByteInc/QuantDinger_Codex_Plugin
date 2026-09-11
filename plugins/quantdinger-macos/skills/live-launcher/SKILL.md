---
name: live-launcher
description: Launch or change a QuantDinger paper or live trading deployment when the user asks to run a strategy, start trading, deploy a strategy, or connect an account for trading.
---

# QuantDinger Live Launcher

Use this workflow to make a trading deployment simple while keeping capital-affecting actions explicit and bounded.

## Required preflight

1. Call `check_health` and `whoami` before taking any action.
2. Call `list_trading_accounts` and `runtime_overview` to establish the available accounts and existing running strategies.
3. Never request, display, store, or infer exchange credentials. QuantDinger owns those credentials.
4. If the server, token, or required trading scope is unavailable, explain the missing setup and stop. Do not suggest bypasses.

## Launch path

1. Identify the user's intended strategy. Use an existing strategy when an ID is provided; otherwise route strategy creation to `strategy-lab`.
2. Present one compact launch card containing the account, strategy, mode, market and symbols, maximum capital, leverage, and relevant stop or loss limits.
3. State whether the deployment is paper or live. Do not imply that a backtest predicts future performance.
4. Ask for a clear in-thread confirmation that repeats the intended mode. Do not accept vague agreement as confirmation.
5. Only after confirmation, call the relevant mutation with a new caller-generated `idempotency_key` and its required confirmation parameter.
6. Read `runtime_overview` and the strategy record afterward. Report the returned state exactly, including an asynchronous `starting` state.

## Direct order path

For `place_quick_order`, show the market, symbol, side, order type, quantity, estimated notional, optional protection prices, and paper/live mode before requesting confirmation. Call it only with `confirm_order=true`; for live mode also require `confirm_live_trading=true`.

## Safety rules

- Never turn paper trading into live trading without a separate explicit confirmation.
- Never modify risk limits, leverage, account selection, or symbols as an unstated side effect.
- Do not retry a mutation with a new idempotency key after an uncertain failure. Inspect the returned state first.
- Do not make investment-performance promises or present a strategy as suitable for the user.

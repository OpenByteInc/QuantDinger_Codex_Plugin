---
name: trading-operations
description: Monitor, explain, pause, stop, or emergency-stop QuantDinger trading when the user asks about active strategies, positions, trades, orders, PnL, or an operational incident.
---

# QuantDinger Trading Operations

Use this workflow for operational visibility and carefully controlled intervention.

## Read path

1. Call `check_health`, `whoami`, and `runtime_overview`.
2. For a selected strategy, use `get_strategy`, `list_strategy_positions`, `list_strategy_trades`, and `list_strategy_pending_orders` as needed.
3. State the facts first: current runtime state, positions, pending orders, and recent fills. Mark any explanation of strategy behavior as an inference.

## Intervention path

Before `stop_strategy`, `cancel_open_paper_orders`, or `emergency_stop_trading`, display what will change and request an explicit confirmation. Use a new `idempotency_key` for each action and the tool's required confirmation flag.

After an intervention, re-read `runtime_overview` and relevant order or position data. Report partial failures and any need for human follow-up; never claim that an exchange order was cancelled without confirmation from QuantDinger.

## Restrictions

- Do not reveal credentials or tokens.
- Do not place a new order while diagnosing or recovering from an incident unless the user begins a separate, explicitly confirmed launch or order request.
- Treat emergency stop as irreversible operational action, not a convenience command.

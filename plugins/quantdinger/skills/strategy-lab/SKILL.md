---
name: strategy-lab
description: Create, compile, save, compare, or backtest a QuantDinger Strategy API V2 strategy when the user asks to turn a market idea or strategy code into a testable trading strategy.
---

# QuantDinger Strategy Lab

Use this workflow to convert an idea into a reproducible strategy artifact, not a trading recommendation.

## Workflow

1. Call `check_health` and `whoami` first.
2. Clarify the market, instruments, frequency, holding style, and risk constraints. Use `list_markets`, `search_symbols`, `get_klines`, templates, universes, or factors only when needed.
3. Call `get_strategy_authoring_contract` and `list_strategy_templates` before generating Strategy API V2 code.
4. Compile code with `compile_strategy_code`. Fix failures before saving or backtesting.
5. Save a compiled source with `save_strategy_source`, using a new `idempotency_key`.
6. Submit a backtest with `submit_backtest`; use the returned job ID and `wait_for_job` or bounded streaming to retrieve its result.
7. Report the code/source version, date range, data provenance, assumptions, return, drawdown, trade count, costs, and known limitations. Distinguish observed data from interpretation.

## Handoff to live trading

A passing compilation or a favorable backtest is not authority to trade. When the user asks to deploy, hand off to `live-launcher`, which must obtain a separate explicit confirmation.

## Restrictions

- The strategy manifest owns market, instrument, frequency, warmup, dependencies, and leverage. Do not invent alternate backtest overrides.
- Every mutating call requires a unique `idempotency_key`.
- Do not save exchange credentials, access tokens, or personally sensitive data in strategy source or parameters.

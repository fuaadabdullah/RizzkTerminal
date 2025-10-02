"""CLI helper to log trades without using the Streamlit UI."""
from __future__ import annotations

import argparse
import datetime as dt

from apps.rizzk_pro.journal import save_trade
from apps.rizzk_pro.risk import validate_trade


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log a trade into the journal database.")
    parser.add_argument("--ticker", required=True, help="Ticker symbol")
    parser.add_argument("--side", choices=["long", "short"], required=True)
    parser.add_argument("--entry", type=float, required=True, help="Entry price")
    parser.add_argument("--stop", type=float, required=True, help="Stop price")
    parser.add_argument("--exit", type=float, default=0.0, help="Target / exit price")
    parser.add_argument("--qty", type=float, default=1.0, help="Quantity")
    parser.add_argument("--risk", type=float, default=0.0, help="Risk override in dollars")
    parser.add_argument("--reward", type=float, default=0.0, help="Reward override in dollars")
    parser.add_argument("--max-risk", type=float, default=10_000.0, help="Risk limit in dollars")
    parser.add_argument("--date", type=str, default=None, help="Trade date (YYYY-MM-DD)")
    parser.add_argument("--thesis", type=str, default="", help="Trade thesis summary")
    parser.add_argument("--notes", type=str, default="", help="Additional notes")
    parser.add_argument("--tags", type=str, default="", help="Comma separated tags")
    return parser.parse_args()


def compute_reward(entry: float, exit_price: float, qty: float, override: float) -> float:
    if override > 0:
        return override
    if exit_price > 0 and qty > 0:
        return abs(exit_price - entry) * qty
    return 0.0


def compute_risk(entry: float, stop: float, qty: float, override: float, limit: float) -> float:
    if override > 0:
        return override
    ok, msg, exposure = validate_trade(entry, stop, qty, limit)
    if not ok:
        raise SystemExit(msg)
    return exposure


def main() -> None:
    args = parse_args()
    trade_date = args.date or dt.datetime.now().strftime("%Y-%m-%d")
    reward = compute_reward(args.entry, args.exit, args.qty, args.reward)
    risk = compute_risk(args.entry, args.stop, args.qty, args.risk, args.max_risk)

    payload = {
        "date": trade_date,
        "ticker": args.ticker.upper(),
        "side": args.side,
        "entry": args.entry,
        "stop": args.stop,
        "exit": args.exit,
        "qty": args.qty,
        "risk": risk,
        "reward": reward,
        "thesis": args.thesis,
        "notes": args.notes,
        "tags": args.tags,
    }

    trade_id, export_path = save_trade(payload)
    print(f"[trade] added {trade_id} -> {export_path}")


if __name__ == "__main__":
    main()

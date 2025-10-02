# rizzk_pro.py  — Rizzk Trading Terminal
from __future__ import annotations

import io
import logging
import logging.handlers
import os
import socket
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests  # type: ignore[import-untyped]
import streamlit as st
import altair as alt
import plotly.graph_objects as go
from dotenv import load_dotenv

from apps.rizzk_pro.journal import (
    DB_PATH as JOURNAL_DB_PATH,
    ensure_dirs as ensure_journal_dirs,
    fetch_trades,
    save_trade,
)
from apps.rizzk_pro.risk import validate_trade

# Optional: load .env if present
load_dotenv(override=False)

# -------- app setup --------
st.set_page_config(page_title="Rizzk Trading Terminal", page_icon="📈", layout="wide")
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)
EXPORTS_DIR = Path(os.getenv("RIZZK_EXPORTS", "obsidian/90_exports"))
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
ensure_journal_dirs()


def _configure_logging() -> logging.Logger:
    """Set up a rotating file handler so exceptions are preserved."""

    logger = logging.getLogger("rizzk")
    if logger.handlers:
        return logger

    handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


logger = _configure_logging()

# -------- sidebar --------
def render_health_sidebar() -> None:
    """Expose minimal environment diagnostics in the sidebar."""

    st.sidebar.markdown("**Health**")
    st.sidebar.write(
        {
            "hostname": socket.gethostname(),
            "vault": os.getenv("RIZZK_VAULT", "obsidian"),
            "exports": str(EXPORTS_DIR),
            "db": str(JOURNAL_DB_PATH),
        }
    )


st.sidebar.header("Settings")
# Allow pasting keys even if not set in env
default_openai = os.environ.get("OPENAI_API_KEY", "")
default_alpha = os.environ.get("ALPHAVANTAGE_API_KEY", "")
user_openai = st.sidebar.text_input("OpenAI API Key (sk-...)", value=default_openai, type="password")
user_alpha = st.sidebar.text_input("Alpha Vantage API Key", value=default_alpha, type="password")
if user_openai:
    os.environ["OPENAI_API_KEY"] = user_openai
if user_alpha:
    os.environ["ALPHAVANTAGE_API_KEY"] = user_alpha

st.sidebar.caption("Tip: persist with `setx OPENAI_API_KEY ...` then reopen PowerShell.")

account_equity = st.sidebar.number_input(
    "Account size ($)", min_value=1000.0, max_value=1_000_000.0, value=25_000.0, step=1_000.0
)
risk_per_trade = st.sidebar.slider("Risk per trade (% of account)", 0.0, 0.05, 0.01, 0.001)
max_daily_loss = st.sidebar.slider("Max daily loss (% of account)", 0.0, 0.20, 0.05, 0.005)
max_risk_dollars = account_equity * risk_per_trade
max_daily_loss_dollars = account_equity * max_daily_loss

st.sidebar.metric("Risk per trade ($)", f"${max_risk_dollars:,.2f}")
st.sidebar.metric("Daily loss limit ($)", f"${max_daily_loss_dollars:,.2f}")

render_health_sidebar()

# -------- utils --------
def normalize_symbol(sym: str) -> str:
    return str(sym).strip().upper()

def stooq_url(sym: str, period: str) -> str:
    m = {"1mo":22, "3mo":66, "6mo":132, "1y":252, "5y":1260, "max":10000}
    n = m.get(period, 132)
    return f"https://stooq.com/q/d/l/?s={sym.lower()}&i=d&c={n}"

@st.cache_data(ttl=600)
def fetch_stooq_history(sym: str, period: str = "6mo") -> pd.DataFrame:
    sym = normalize_symbol(sym)
    try:
        r = requests.get(stooq_url(sym, period), timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty:
            raise ValueError("empty")
        df.columns = [c.title() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        for c in ["Open", "High", "Low", "Close", "Volume"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["Date","Close"]).sort_values("Date").reset_index(drop=True)
        df["Symbol"] = sym
        return df
    except Exception:
        logger.exception("Falling back to synthetic data for %s", sym)
        idx = pd.date_range(end=datetime.today(), periods=120, freq="B")
        base = 100 + np.cumsum(np.random.normal(0, 1, size=len(idx)))
        df = pd.DataFrame(
            {
                "Date": idx,
                "Open": base,
                "High": base + np.random.uniform(0.2, 1.0, size=len(idx)),
                "Low": base - np.random.uniform(0.2, 1.0, size=len(idx)),
                "Close": base + np.random.normal(0, 0.5, size=len(idx)),
                "Volume": np.random.randint(100_000, 2_000_000, size=len(idx)),
                "Symbol": sym,
            }
        )
        return df

def as_float_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("float64")

def sma(series: pd.Series, win: int) -> pd.Series:
    s = as_float_series(series)
    return s.rolling(win, min_periods=1).mean()

def rsi(series: pd.Series, win: int = 14) -> pd.Series:
    s = as_float_series(series)
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(win, min_periods=1).mean()
    roll_down = down.rolling(win, min_periods=1).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def export_watchlist(df: pd.DataFrame, name: str = "watchlist") -> Path:
    """Persist the supplied DataFrame into the exports vault folder."""

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_name = name.replace(" ", "_").lower()
    target = EXPORTS_DIR / f"{safe_name}_{ts}.csv"
    df.to_csv(target, index=False)
    return target

# Market clock (America/New_York)
NY_TZ = ZoneInfo("America/New_York")


def ny_session_bounds(reference: datetime) -> tuple[datetime, datetime]:
    ref = reference if reference.tzinfo else reference.replace(tzinfo=NY_TZ)
    ref_ny = ref.astimezone(NY_TZ)
    open_dt = datetime.combine(ref_ny.date(), time(9, 30), tzinfo=NY_TZ)
    close_dt = datetime.combine(ref_ny.date(), time(16, 0), tzinfo=NY_TZ)
    return open_dt, close_dt


def is_market_open(now: datetime) -> bool:
    ref = now if now.tzinfo else now.replace(tzinfo=NY_TZ)
    wd = ref.astimezone(NY_TZ).weekday()
    if wd >= 5:
        return False
    open_dt, close_dt = ny_session_bounds(now)
    return open_dt <= now <= close_dt


def next_market_event(now: datetime) -> str:
    if is_market_open(now):
        close_dt = ny_session_bounds(now)[1]
        return f"Market OPEN until {close_dt.strftime('%I:%M %p %Z')}"

    next_open, _ = ny_session_bounds(now)
    if now >= next_open:
        next_day = now + timedelta(days=1)
        next_open, _ = ny_session_bounds(next_day)

    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)

    return f"Next open: {next_open.strftime('%a %b %d, %I:%M %p %Z')}"

# Alpha Vantage News
@st.cache_data(ttl=600)
def fetch_av_news(tickers: tuple[str, ...], limit: int = 20) -> List[Dict[str, Any]]:
    key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
    if not key:
        return []
    # AlphaVantage supports comma-delimited tickers
    sym = ",".join([normalize_symbol(s) for s in tickers if s.strip()]) or "AAPL"
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={sym}&limit={limit}&apikey={key}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("feed", [])
    except Exception:
        logger.exception("Alpha Vantage news fetch failed")
        return []

# -------- UI --------
st.title("Rizzk Trading Terminal 📈")
now = datetime.now(tz=NY_TZ)
st.caption("Education only. Not financial advice.")
st.info(("🟢 " if is_market_open(now) else "🔴 ") + next_market_event(now))

tabs = st.tabs(["Prices", "Backtest", "Screener", "Journal", "News", "AI Assistant"])

# Prices
with tabs[0]:
    c1, c2, c3, c4 = st.columns([2,1,1,1])
    with c1:
        px_sym = st.text_input("Symbol", value="AAPL").strip()
    with c2:
        period = st.selectbox("Period", ["1mo","3mo","6mo","1y","5y","max"], index=2)
    with c3:
        show_rsi = st.checkbox("Show RSI", True)
    with c4:
        show_sma = st.checkbox("Show SMA(20/50)", True)

    if st.button("Fetch", type="primary", key="fetch_px"):
        df = fetch_stooq_history(px_sym, period)
        if df.empty:
            st.warning("No data returned.")
        else:
            st.dataframe(df.tail(10), use_container_width=True)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"
            ))
            if show_sma:
                fig.add_trace(go.Scatter(x=df["Date"], y=sma(df["Close"], 20), name="SMA 20", mode="lines"))
                fig.add_trace(go.Scatter(x=df["Date"], y=sma(df["Close"], 50), name="SMA 50", mode="lines"))
            fig.update_layout(height=420, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)

            if show_rsi:
                rs = rsi(df["Close"], 14)
                c = alt.Chart(pd.DataFrame({"Date": df["Date"], "RSI": rs})).mark_line().encode(
                    x="Date:T", y=alt.Y("RSI:Q", scale=alt.Scale(domain=[0,100]))
                )
                st.altair_chart(c, use_container_width=True)

            export_path = export_watchlist(df, f"prices_{normalize_symbol(px_sym)}_{period}")
            st.success(f"Saved latest dataset to `{export_path}` for the vault sync daemon.")

# Backtest
def backtest_sma_cross(df: pd.DataFrame, short: int = 10, long: int = 20, fee_bps: float = 1.0) -> Dict[str, Any]:
    px = as_float_series(df["Close"]).fillna(0.0)
    s_sma = sma(px, short)
    l_sma = sma(px, long)
    signal = (s_sma > l_sma).astype(int)
    shift_sig = signal.shift(1).fillna(0)
    toggles = (signal != shift_sig).astype(int)
    ret = px.pct_change().fillna(0.0)
    strat_ret = ret * signal
    cost = toggles * (fee_bps / 10000.0)
    strat_ret = strat_ret - cost
    eq_bh = (1 + ret).cumprod()
    eq_st = (1 + strat_ret).cumprod()

    def _stats(eq: pd.Series) -> Dict[str,float]:
        rets = eq.pct_change().fillna(0.0)
        cagr = (eq.iloc[-1] ** (252.0 / max(len(eq),1))) - 1.0
        vol = rets.std() * np.sqrt(252.0)
        dd = (eq / eq.cummax() - 1.0).min()
        sharpe = (rets.mean()*252.0) / (vol if vol != 0 else np.nan)
        return {
            "CAGR": float(cagr) if np.isfinite(cagr) else 0.0,
            "Vol": float(vol) if np.isfinite(vol) else 0.0,
            "MaxDD": float(dd) if np.isfinite(dd) else 0.0,
            "Sharpe": float(sharpe) if np.isfinite(sharpe) else 0.0,
        }

    return {"eq_bh": eq_bh, "eq_st": eq_st, "signal": signal, "stats_bh": _stats(eq_bh), "stats_st": _stats(eq_st)}

with tabs[1]:
    st.subheader("SMA Cross Backtest")
    bt_sym = st.text_input("Backtest Symbol", value="AAPL", key="bt_sym")
    col1, col2, col3 = st.columns(3)
    with col1:
        short = st.number_input("Short SMA", 2, 200, 10, 1)
    with col2:
        long = st.number_input("Long SMA", 3, 300, 20, 1)
    with col3:
        fee_bps = st.number_input("Fee (bps per toggle)", 0.0, 50.0, 1.0, 0.5)

    if st.button("Run Backtest", type="primary"):
        df = fetch_stooq_history(bt_sym, "1y")
        if df.empty:
            st.warning("No data.")
        else:
            res = backtest_sma_cross(df, int(short), int(long), float(fee_bps))
            eq_bh, eq_st = res["eq_bh"], res["eq_st"]

            plot_df = pd.DataFrame({"Date": df["Date"], "Buy&Hold": eq_bh, "Strategy": eq_st})
            line = alt.Chart(plot_df.melt("Date")).mark_line().encode(
                x="Date:T", y="value:Q", color="variable:N"
            )
            st.altair_chart(line, use_container_width=True)

            st.write("**Stats**")
            stats_df = pd.DataFrame([
                {"Model": "Buy&Hold", **res["stats_bh"]},
                {"Model": "Strategy", **res["stats_st"]}
            ])
            st.dataframe(stats_df, use_container_width=True)

            dd_df = pd.DataFrame({
                "Date": df["Date"],
                "BH Drawdown": (eq_bh / eq_bh.cummax() - 1.0),
                "ST Drawdown": (eq_st / eq_st.cummax() - 1.0),
            })
            dd_chart = alt.Chart(dd_df.melt("Date")).mark_area(opacity=0.5).encode(
                x="Date:T", y=alt.Y("value:Q", axis=alt.Axis(format="%")), color="variable:N"
            )
            st.altair_chart(dd_chart, use_container_width=True)

# Screener
@st.cache_data(ttl=600)
def _yah_predefined(name: str) -> List[Dict[str, Any]]:
    mapping = {"Most Active":"most_actives","Top Gainers":"day_gainers","Top Losers":"day_losers"}
    scr_id = mapping.get(name, "")
    if not scr_id:
        return []
    url = f"https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds={scr_id}&count=25&lang=en-US&region=US"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data.get("finance", {}).get("result", [])
        quotes = (result[0].get("quotes", []) if result else [])
        return quotes if isinstance(quotes, list) else []
    except Exception:
        logger.exception("Yahoo predefined screener fetch failed", extra={"list": name})
        return []

@st.cache_data(ttl=600)
def _yah_trending() -> List[Dict[str, Any]]:
    url = "https://query1.finance.yahoo.com/v1/finance/trending/us?lang=en-US&region=US"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        result = data.get("finance", {}).get("result", [])
        quotes = (result[0].get("quotes", []) if result else [])
        return quotes if isinstance(quotes, list) else []
    except Exception:
        logger.exception("Yahoo trending fetch failed")
        return []

with tabs[2]:
    st.subheader("Quick Screeners (Yahoo public)")
    opt = st.selectbox("List", ["Trending","Most Active","Top Gainers","Top Losers"], index=0)
    if st.button("Fetch List", key="screen_fetch"):
        q = _yah_trending() if opt == "Trending" else _yah_predefined(opt)
        if not q:
            st.warning("No data (endpoint rate-limited). Try again later.")
        else:
            dfq = pd.DataFrame(q)
            rename = {
                "symbol":"Symbol","shortName":"Name","regularMarketPrice":"Price",
                "regularMarketChange":"Change","regularMarketChangePercent":"Change%",
                "marketCap":"MktCap","regularMarketVolume":"Volume",
            }
            cols = [c for c in rename.keys() if c in dfq.columns]
            view = dfq[cols].rename(columns=rename)
            st.dataframe(view, use_container_width=True)

            export_name = f"screener_{opt.replace(' ', '_').lower()}"
            export_path = export_watchlist(view, export_name)
            st.info(f"Exported screener results to `{export_path}`.")

# Journal
with tabs[3]:
    st.subheader("Trading Journal")
    st.caption("Trades persist to SQLite and emit markdown receipts into the Obsidian vault.")

    with st.form("trade_entry"):
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_date = st.date_input("Date", value=datetime.now().date())
            trade_ticker = st.text_input("Ticker", value="AAPL").strip().upper()
            trade_side = st.selectbox("Side", ["long", "short"], index=0)
        with col2:
            entry_price = st.number_input("Entry", min_value=0.0, value=100.0, step=0.01)
            stop_price = st.number_input("Stop", min_value=0.0, value=95.0, step=0.01)
            exit_price = st.number_input("Target / Exit", min_value=0.0, value=110.0, step=0.01)
        with col3:
            quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
            override_risk = st.number_input("Risk override ($)", min_value=0.0, value=0.0, step=10.0)
            override_reward = st.number_input("Reward override ($)", min_value=0.0, value=0.0, step=10.0)

        thesis = st.text_input("Thesis", value="")
        notes = st.text_area("Notes", value="", height=120)
        tags = st.text_input("Tags (comma separated)", value="")

        submitted = st.form_submit_button("Save Trade", type="primary")

    if submitted:
        if not trade_ticker:
            st.error("Ticker is required.")
        else:
            is_valid, validation_msg, exposure = validate_trade(entry_price, stop_price, quantity, max_risk_dollars)
            if not is_valid:
                st.error(validation_msg)
            else:
                risk_value = override_risk if override_risk > 0 else exposure
                reward_value = override_reward
                if reward_value <= 0 and exit_price and entry_price:
                    reward_value = abs(exit_price - entry_price) * quantity

                payload = {
                    "date": trade_date.isoformat(),
                    "ticker": trade_ticker,
                    "side": trade_side,
                    "entry": entry_price,
                    "stop": stop_price,
                    "exit": exit_price,
                    "qty": quantity,
                    "risk": risk_value,
                    "reward": reward_value,
                    "thesis": thesis,
                    "notes": notes,
                    "tags": tags,
                }
                trade_id, export_path = save_trade(payload)
                st.success(f"Trade `{trade_id}` saved. Vault note: `{export_path}`")

    trades_df = fetch_trades()
    if not trades_df.empty:
        trades_df["date"] = pd.to_datetime(trades_df["date"]).dt.date
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        metrics_col1.metric("Total trades", len(trades_df))
        avg_rr = trades_df["rr"].dropna()
        metrics_col2.metric("Avg R:R", f"{avg_rr.mean():.2f}" if not avg_rr.empty else "-")
        metrics_col3.metric("Win % (RR>1)", f"{(avg_rr.gt(1).mean() * 100):.1f}%" if not avg_rr.empty else "-")

        st.dataframe(trades_df, use_container_width=True)
    else:
        st.info("No trades logged yet.")

# News
with tabs[4]:
    st.subheader("News (Alpha Vantage)")
    tickers = st.text_input("Tickers (comma sep)", "AAPL,MSFT,SPY")
    if st.button("Fetch News", key="news_fetch"):
        feed = fetch_av_news(tuple(s.strip() for s in tickers.split(",") if s.strip()), limit=30)
        if not feed:
            st.warning("No news returned (missing key or rate-limited).")
        else:
            # Basic table
            rows = []
            for item in feed:
                rows.append({
                    "time": item.get("time_published", ""),
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "ticker_sentiment": ", ".join([t.get("ticker", "") for t in item.get("ticker_sentiment", [])])
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

# AI Assistant
with tabs[5]:
    st.subheader("AI Trading Assistant")
    st.caption("Ask about indicators, entries, exits, risk, or how to use this app.")
    try:
        import openai  # legacy SDK 0.28.1
        openai_available = True
    except ImportError:
        openai = None
        openai_available = False

    if not openai_available:
        st.warning("OpenAI SDK not installed. Install `openai` to enable the assistant.")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role":"system","content":"You are a concise, realistic trading assistant. Be practical. Explain entries/exits, risk, and how to use this app."}]

        # render chat history
        for m in st.session_state.messages[1:]:
            with st.chat_message("user" if m["role"]=="user" else "assistant"):
                st.write(m["content"])

        prompt = st.chat_input("Ask something about markets or this app...")
        if prompt:
            st.session_state.messages.append({"role":"user","content":prompt})
            key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not key:
                st.warning("Add an OpenAI API key in the sidebar to enable responses.")
            else:
                with st.chat_message("assistant"):
                    try:
                        openai.api_key = key
                        completion = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=st.session_state.messages,
                            temperature=0.4,
                        )
                        answer = completion["choices"][0]["message"]["content"].strip()
                        st.session_state.messages.append({"role":"assistant","content":answer})
                        st.write(answer)
                    except Exception:
                        logger.exception("Assistant error")
                        st.error("Assistant error: check logs for details.")

"""
Portfolio Tracker with Telegram Alerts
Tracks NSE stocks and index options P&L.
Sends Telegram alert when P&L first crosses into profit (green) or loss (red).
"""

import json
import os
import time
import sys
from datetime import datetime, time as dtime
import pytz
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# Shared session so NSE cookies are maintained
_nse_session = requests.Session()
_nse_session.headers.update(NSE_HEADERS)
_nse_session_initialized = False


# ---------------------------------------------------------------------------
# NSE session initialization (get cookies)
# ---------------------------------------------------------------------------
def _init_nse_session():
    global _nse_session_initialized
    if _nse_session_initialized:
        return
    try:
        _nse_session.get("https://www.nseindia.com/", timeout=10)
        _nse_session_initialized = True
    except Exception as exc:
        print(f"[WARN] Could not initialize NSE session: {exc}")


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------
def fetch_stock_price(symbol: str) -> float | None:
    """Fetch LTP for an NSE equity symbol."""
    _init_nse_session()
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}"
    try:
        resp = _nse_session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ltp = (
            data.get("priceInfo", {}).get("lastPrice")
            or data.get("priceInfo", {}).get("close")
        )
        return float(ltp) if ltp is not None else None
    except Exception as exc:
        print(f"[ERROR] fetch_stock_price({symbol}): {exc}")
        return None


def fetch_option_price(
    symbol: str, option_type: str, strike: float, expiry: str
) -> float | None:
    """
    Fetch LTP for an index option from NSE option chain.

    symbol      : 'NIFTY' | 'BANKNIFTY' | 'FINNIFTY' etc.
    option_type : 'CE' | 'PE'
    strike      : numeric strike price
    expiry      : expiry date string as it appears in NSE API (e.g. '27-Mar-2026')
    """
    _init_nse_session()
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
    try:
        resp = _nse_session.get(url, timeout=15)
        resp.raise_for_status()
        records = resp.json().get("records", {}).get("data", [])
        for row in records:
            if (
                row.get("strikePrice") == strike
                and row.get("expiryDate", "").lower() == expiry.lower()
                and option_type.upper() in row
            ):
                ltp = row[option_type.upper()].get("lastPrice")
                return float(ltp) if ltp is not None else None
        print(f"[WARN] Option not found: {symbol} {strike} {option_type} {expiry}")
        return None
    except Exception as exc:
        print(f"[ERROR] fetch_option_price({symbol} {strike} {option_type}): {exc}")
        return None


def fetch_price(position: dict) -> float | None:
    """Dispatch to the correct price fetcher based on position type."""
    ptype = position["type"].lower()
    if ptype == "stock":
        return fetch_stock_price(position["symbol"])
    elif ptype == "option":
        return fetch_option_price(
            position["symbol"],
            position["option_type"],
            position["strike"],
            position["expiry"],
        )
    else:
        print(f"[ERROR] Unknown position type: {ptype}")
        return None


# ---------------------------------------------------------------------------
# P&L calculation
# ---------------------------------------------------------------------------
def calculate_pnl(position: dict, current_price: float) -> float:
    avg = position["avg_price"]
    qty = position["quantity"]
    if position["type"].lower() == "option":
        lot_size = position.get("lot_size", 1)
        return (current_price - avg) * qty * lot_size
    return (current_price - avg) * qty


# ---------------------------------------------------------------------------
# Telegram notification
# ---------------------------------------------------------------------------
def send_telegram(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Telegram credentials not set. Alert not sent.")
        print(f"[ALERT MESSAGE]\n{message}")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        if resp.ok:
            return True
        print(f"[ERROR] Telegram send failed: {resp.text}")
        return False
    except Exception as exc:
        print(f"[ERROR] Telegram exception: {exc}")
        return False


# ---------------------------------------------------------------------------
# Alert state tracker
# ---------------------------------------------------------------------------
class AlertStateTracker:
    """
    Tracks green/red state per label.
    Fires an alert whenever P&L crosses from one side to the other.
    """

    def __init__(self):
        self._states: dict[str, str | None] = {}

    def check(self, label: str, pnl: float, position: dict | None = None) -> str | None:
        """
        Returns an alert message string if this is a first-touch crossing,
        otherwise returns None. Updates internal state.
        """
        prev = self._states.get(label)

        if pnl > 0:
            new_state = "green"
        elif pnl < 0:
            new_state = "red"
        else:
            # Exactly zero — no state change, no alert
            return None

        self._states[label] = new_state

        if new_state == prev:
            return None  # Same state — no alert

        # State changed — build alert message
        now_ist = datetime.now(IST).strftime("%H:%M:%S IST")
        sign = "+" if pnl >= 0 else ""

        if new_state == "green":
            header = "🟢 <b>FIRST TOUCH GREEN</b>"
        else:
            header = "🔴 <b>FIRST TOUCH RED</b>"

        if position is not None:
            pos_label = _position_display_name(position)
            avg = position["avg_price"]
            # current_price back-calculated for display
            if position["type"].lower() == "option":
                lot_size = position.get("lot_size", 1)
                qty = position["quantity"]
                current_price = avg + pnl / (qty * lot_size)
            else:
                qty = position["quantity"]
                current_price = avg + pnl / qty

            msg = (
                f"{header}\n"
                f"Position: {pos_label}\n"
                f"P&amp;L: {sign}₹{abs(pnl):,.2f}\n"
                f"Entry: ₹{avg:,.2f} | LTP: ₹{current_price:,.2f}\n"
                f"Time: {now_ist}"
            )
        else:
            msg = (
                f"{header} — <b>PORTFOLIO OVERALL</b>\n"
                f"Total P&amp;L: {sign}₹{abs(pnl):,.2f}\n"
                f"Time: {now_ist}"
            )

        return msg


def _position_display_name(position: dict) -> str:
    if position["type"].lower() == "option":
        return (
            f"{position['symbol']} {int(position['strike'])} "
            f"{position['option_type']} ({position['expiry']})"
        )
    return f"{position['symbol']} (stock)"


# ---------------------------------------------------------------------------
# Market hours guard
# ---------------------------------------------------------------------------
def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


# ---------------------------------------------------------------------------
# Console summary table
# ---------------------------------------------------------------------------
def print_summary(results: list[dict], total_pnl: float):
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    print(f"\n{'─'*70}")
    print(f"  Portfolio Summary  |  {now_str}")
    print(f"{'─'*70}")
    print(f"  {'Position':<35} {'Avg':>10} {'LTP':>10} {'P&L':>12}")
    print(f"{'─'*70}")
    for r in results:
        name = _position_display_name(r["position"])[:34]
        avg = r["position"]["avg_price"]
        ltp = r.get("ltp")
        pnl = r.get("pnl")
        ltp_str = f"₹{ltp:,.2f}" if ltp is not None else "N/A"
        pnl_str = (
            f"+₹{pnl:,.2f}" if pnl and pnl >= 0
            else f"-₹{abs(pnl):,.2f}" if pnl is not None
            else "N/A"
        )
        print(f"  {name:<35} ₹{avg:>9,.2f} {ltp_str:>10} {pnl_str:>12}")
    print(f"{'─'*70}")
    sign = "+" if total_pnl >= 0 else ""
    print(f"  {'TOTAL P&L':<57} {sign}₹{total_pnl:,.2f}")
    print(f"{'─'*70}\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
        config = json.load(f)

    positions = config["positions"]
    poll_interval = config.get("poll_interval_seconds", 10)
    tracker = AlertStateTracker()

    print("=" * 70)
    print("  NSE Portfolio Tracker with Telegram Alerts")
    print(f"  Tracking {len(positions)} position(s) | Poll every {poll_interval}s")
    print("  Press Ctrl+C to stop.")
    print("=" * 70)

    while True:
        if not is_market_open():
            now = datetime.now(IST)
            print(
                f"[{now.strftime('%H:%M:%S IST')}] Market closed. "
                "Waiting... (Ctrl+C to exit)"
            )
            time.sleep(60)
            continue

        results = []
        total_pnl = 0.0

        for pos in positions:
            ltp = fetch_price(pos)
            pnl = None
            if ltp is not None:
                pnl = calculate_pnl(pos, ltp)
                total_pnl += pnl

                # Per-position alert
                label = _position_display_name(pos)
                alert_msg = tracker.check(label, pnl, pos)
                if alert_msg:
                    print(f"\n[ALERT] {label}")
                    send_telegram(alert_msg)

            results.append({"position": pos, "ltp": ltp, "pnl": pnl})

        # Overall portfolio alert
        overall_alert = tracker.check("__overall__", total_pnl, None)
        if overall_alert:
            print("\n[ALERT] Overall portfolio state changed!")
            send_telegram(overall_alert)

        print_summary(results, total_pnl)
        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTracker stopped.")
        sys.exit(0)

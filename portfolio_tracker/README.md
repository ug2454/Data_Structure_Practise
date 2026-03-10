# NSE Portfolio Tracker with Telegram Alerts

Tracks your stock and options positions using free NSE public APIs.
Sends a **Telegram message** the moment your P&L first crosses into profit (🟢 green) or loss (🔴 red) — both per position and for the overall portfolio.

---

## Features

- Live LTP from NSE (no Zerodha API key needed)
- Tracks **equity stocks** and **index options** (Nifty, BankNifty, etc.)
- Fires alert on **first touch green** and **first touch red** — per position and total portfolio
- Console summary table printed every poll cycle
- Automatically skips polling outside market hours (09:15–15:30 IST, Mon–Fri)

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install pytz   # timezone support
```

### 2. Create your `.env` file

Copy the template and fill in your Telegram credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNOPqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321
```

**How to get these:**
- **Bot token**: Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token.
- **Chat ID**: Message [@userinfobot](https://t.me/userinfobot) on Telegram → it replies with your chat ID.

### 3. Edit `config.json` with your positions

```json
{
  "poll_interval_seconds": 10,
  "positions": [
    {
      "type": "stock",
      "symbol": "INFY",
      "quantity": 10,
      "avg_price": 1500.0
    },
    {
      "type": "option",
      "symbol": "NIFTY",
      "option_type": "CE",
      "strike": 22000,
      "expiry": "27-Mar-2026",
      "lot_size": 75,
      "quantity": 1,
      "avg_price": 150.0
    }
  ]
}
```

**Field reference:**

| Field | Required for | Description |
|---|---|---|
| `type` | both | `"stock"` or `"option"` |
| `symbol` | both | NSE symbol e.g. `"INFY"`, `"NIFTY"` |
| `quantity` | both | Number of shares / lots |
| `avg_price` | both | Your average buy price |
| `option_type` | option | `"CE"` (Call) or `"PE"` (Put) |
| `strike` | option | Strike price as a number e.g. `22000` |
| `expiry` | option | Expiry date exactly as shown on NSE e.g. `"27-Mar-2026"` |
| `lot_size` | option | Lot size for the index e.g. `75` for Nifty |

### 4. Run

```bash
python tracker.py
```

---

## Alert Examples

**First touch green (per position):**
```
🟢 FIRST TOUCH GREEN
Position: NIFTY 22000 CE (27-Mar-2026)
P&L: +₹1,125.00
Entry: ₹150.00 | LTP: ₹165.00
Time: 10:32:05 IST
```

**First touch red (overall portfolio):**
```
🔴 FIRST TOUCH RED — PORTFOLIO OVERALL
Total P&L: -₹2,340.00
Time: 11:15:22 IST
```

---

## Testing alerts without waiting

To test that Telegram alerts work immediately, temporarily change a position's `avg_price` to a value above the current market price — this forces a red P&L. Then change it below the market price to trigger a green alert.

---

## Notes

- NSE APIs are publicly accessible but may occasionally return errors during high traffic. Failures are logged and the tracker continues.
- Alerts fire on **every** green↔red crossing, not just the first of the day.
- To stop the tracker, press **Ctrl+C**.

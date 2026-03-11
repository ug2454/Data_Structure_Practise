"""Quick NSE API diagnostic — run this directly to see raw responses."""
import time
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}

s = requests.Session()
s.headers.update(HEADERS)


def get(url, label, referer=None, delay=3):
    if referer:
        s.headers["Referer"] = referer
    print(f"\n{label}")
    r = s.get(url, timeout=15)
    print(f"  Status      : {r.status_code}")
    print(f"  Cookies     : {list(s.cookies.keys())}")
    time.sleep(delay)
    return r


print("=" * 60)
get("https://www.nseindia.com/", "Step 1: Homepage warm-up", delay=4)
get("https://www.nseindia.com/market-data/live-equity-market",
    "Step 2: Equity market page", referer="https://www.nseindia.com/", delay=3)
get("https://www.nseindia.com/option-chain",
    "Step 3: Option chain page",
    referer="https://www.nseindia.com/market-data/live-equity-market", delay=4)

print("\nStep 4: API call")
r = get(
    "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
    "Step 4: option-chain-indices API",
    referer="https://www.nseindia.com/option-chain",
    delay=0,
)
print(f"  Content-Type: {r.headers.get('Content-Type', '?')}")
print(f"  Body[:300]  : {r.text[:300]!r}")

try:
    data = r.json()
    records = data.get("records", {}).get("data", [])
    expiries = sorted({row.get("expiryDate") for row in records if row.get("expiryDate")})
    print(f"\n  records.data length : {len(records)}")
    print(f"  Available expiries  : {expiries}")
    if records:
        print(f"  Sample record keys  : {list(records[0].keys())}")
    else:
        print("\n  STILL EMPTY — NSE is blocking this session (Akamai bot detection)")
        print("  Try: pip install cloudscraper  and replace requests.Session() with cloudscraper.create_scraper()")
except Exception as e:
    print(f"\n  JSON parse failed: {e}")

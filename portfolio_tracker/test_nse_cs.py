"""NSE API test using cloudscraper to bypass Akamai bot detection."""
import time

try:
    import cloudscraper
except ImportError:
    print("Run: pip install cloudscraper")
    raise

s = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
)

def get(url, label, referer=None, delay=3):
    if referer:
        s.headers["Referer"] = referer
    print(f"\n{label}")
    r = s.get(url, timeout=20)
    print(f"  Status  : {r.status_code}")
    print(f"  Cookies : {list(s.cookies.keys())}")
    time.sleep(delay)
    return r

print("=" * 60)
get("https://www.nseindia.com/", "Step 1: Homepage", delay=4)
get("https://www.nseindia.com/option-chain", "Step 2: Option chain page",
    referer="https://www.nseindia.com/", delay=5)

r = get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
        "Step 3: API call",
        referer="https://www.nseindia.com/option-chain", delay=0)

print(f"\n  Body[:400] : {r.text[:400]!r}")
try:
    data = r.json()
    records = data.get("records", {}).get("data", [])
    expiries = sorted({row.get("expiryDate") for row in records if row.get("expiryDate")})
    print(f"  records    : {len(records)}")
    print(f"  expiries   : {expiries}")
    if records:
        print(f"  keys       : {list(records[0].keys())}")
        print("\n  SUCCESS — API is working!")
    else:
        print("\n  FAILED — still empty even with cloudscraper")
except Exception as e:
    print(f"  JSON parse failed: {e}")

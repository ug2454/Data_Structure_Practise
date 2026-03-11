"""Quick NSE API diagnostic — run this directly to see raw responses."""
import time
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/option-chain",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}

s = requests.Session()
s.headers.update(HEADERS)

print("=" * 60)
print("Step 1: GET https://www.nseindia.com/")
r = s.get("https://www.nseindia.com/", timeout=10)
print(f"  Status : {r.status_code}")
print(f"  Cookies: {dict(s.cookies)}")
time.sleep(2)

print("\nStep 2: GET https://www.nseindia.com/option-chain")
r = s.get("https://www.nseindia.com/option-chain", timeout=10)
print(f"  Status : {r.status_code}")
print(f"  Cookies: {dict(s.cookies)}")
time.sleep(2)

print("\nStep 3: GET option-chain-indices API")
url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
r = s.get(url, timeout=15)
print(f"  Status      : {r.status_code}")
print(f"  Content-Type: {r.headers.get('Content-Type', '?')}")
print(f"  Body[:500]  : {r.text[:500]!r}")

try:
    data = r.json()
    records = data.get("records", {}).get("data", [])
    expiries = sorted({row.get("expiryDate") for row in records if row.get("expiryDate")})
    print(f"\n  records.data length : {len(records)}")
    print(f"  Available expiries  : {expiries}")
except Exception as e:
    print(f"\n  JSON parse failed: {e}")

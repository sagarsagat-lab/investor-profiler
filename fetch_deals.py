"""
Step 1: download NSE bulk and block deals for every tracked company.
Run this on a PC with internet access (NSE blocks most cloud IPs).
Output: data/deals.csv  columns: Date, Symbol, Client, Side, Qty, Price, DealKind
"""
import datetime as dt
import pandas as pd
import requests
from config import COMPANIES, DATA, START_DATE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/",
}

# NSE field names have changed over time; map both old and new names.
COLUMN_MAP = {
    "BD_DT_DATE": "Date", "date": "Date",
    "BD_SYMBOL": "Symbol", "symbol": "Symbol",
    "BD_CLT_NAME": "Client", "clientName": "Client",
    "BD_BUY_SELL": "Side", "buySell": "Side", "dealType": "Side",
    "BD_QTY_TRD": "Qty", "quantity": "Qty",
    "BD_TP_WATP": "Price", "price": "Price",
}


def nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get("https://www.nseindia.com", timeout=20)  # sets the cookies NSE needs
    return s


def yearly_windows(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        nxt = min(dt.date(cur.year, 12, 31), end)
        yield cur, nxt
        cur = nxt + dt.timedelta(days=1)


def fetch(s, kind: str, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    url = f"https://www.nseindia.com/api/historical/{kind}-deals"
    params = {"symbol": symbol, "from": start.strftime("%d-%m-%Y"), "to": end.strftime("%d-%m-%Y")}
    r = s.get(url, params=params, timeout=30)
    r.raise_for_status()
    rows = r.json().get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).rename(columns=COLUMN_MAP)
    df = df[[c for c in ["Date", "Symbol", "Client", "Side", "Qty", "Price"] if c in df.columns]].copy()
    df["DealKind"] = "bulk" if kind == "bulk" else "block"
    return df


def main():
    DATA.mkdir(exist_ok=True)
    s = nse_session()
    start = dt.date.fromisoformat(START_DATE)
    end = dt.date.today()
    frames = []
    for sym in COMPANIES:
        for kind in ("bulk", "block"):
            for a, b in yearly_windows(start, end):
                try:
                    df = fetch(s, kind, sym, a, b)
                    if not df.empty:
                        frames.append(df)
                except Exception as exc:  # keep going; report at the end
                    print(f"[warn] {sym} {kind} {a}..{b}: {exc}")
        print(f"[ok] {sym}")
    if not frames:
        raise SystemExit("No deals fetched. Check the NSE connection or the column mapping.")
    out = pd.concat(frames, ignore_index=True)
    out["Date"] = pd.to_datetime(out["Date"], dayfirst=True, errors="coerce")
    out["Qty"] = pd.to_numeric(out["Qty"].astype(str).str.replace(",", ""), errors="coerce")
    out["Price"] = pd.to_numeric(out["Price"].astype(str).str.replace(",", ""), errors="coerce")
    out["Side"] = out["Side"].astype(str).str.upper().str[0].map({"B": "BUY", "S": "SELL"})
    out = out.dropna(subset=["Date", "Qty", "Price", "Side"]).drop_duplicates()
    out.to_csv(DATA / "deals.csv", index=False)
    print(f"Saved {len(out)} deals to {DATA / 'deals.csv'}")


if __name__ == "__main__":
    main()

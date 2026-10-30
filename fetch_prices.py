"""
Step 2: download daily closing prices (split/bonus adjusted) for tracked companies.
Needs: pip install yfinance pandas
Output: data/prices.csv  columns: Date, Symbol, Close
"""
import pandas as pd
from config import COMPANIES, DATA, START_DATE


def main():
    import yfinance as yf  # imported here so --offline runs work without it
    DATA.mkdir(exist_ok=True)
    tickers = [f"{s}.NS" for s in COMPANIES]
    raw = yf.download(tickers, start=START_DATE, auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": COMPANIES[0] + ".NS"})
    close.columns = [c.replace(".NS", "") for c in close.columns]
    long = close.stack().reset_index()
    long.columns = ["Date", "Symbol", "Close"]
    long = long.dropna().sort_values(["Symbol", "Date"])
    long.to_csv(DATA / "prices.csv", index=False)
    print(f"Saved {len(long)} price rows to {DATA / 'prices.csv'}")


if __name__ == "__main__":
    main()

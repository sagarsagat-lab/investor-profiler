"""
Step 4: turn deals + prices into investor profiles.

Definitions (also shown on the dashboard):
  Round trip   : a buy lot matched FIFO to a later sell of the same stock by the same client.
  Holding days : days between buy and sell (round trips) or first buy and as-of date (open positions).
  CAGR         : annualised return = (exit / entry) ** (365 / days) - 1. Needs at least 30 days.
  Current value: open quantity x latest close.
  Buy style    : buy price vs the 52-week high on the day of the buy.
                 < 85% of high = 'Buys dips'; > 97% = 'Buys strength'; otherwise 'Buys mid-range'.
  Horizon      : average holding days < 90 = Short-term; 90-365 = Medium-term; > 365 = Long-term.
  Unmatched names are 'Unclassified' so you can review them, not guessed as individuals.
  Investor type is rule-based (config.TYPE_RULES) and can be overridden in data/client_types_override.csv.
"""
import json
import re
import statistics
from collections import defaultdict
import pandas as pd
from config import DATA, OUT, TYPE_RULES


def classify(name: str, overrides: dict) -> str:
    if name in overrides:
        return overrides[name]
    for label, pat in TYPE_RULES:
        if re.search(pat, name, re.I):
            return label
    return "Unclassified (review name)"


def load_overrides() -> dict:
    p = DATA / "client_types_override.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return dict(zip(df["Client"], df["Type"]))


def fifo_round_trips(trades: pd.DataFrame):
    """trades: one client-stock group sorted by date. Returns (round_trips, open_lots)."""
    lots, closed = [], []
    for _, t in trades.iterrows():
        if t["Side"] == "BUY":
            lots.append([t["Date"], float(t["Qty"]), float(t["Price"])])
            continue
        q = float(t["Qty"])
        while q > 1e-9 and lots:
            ld, lq, lp = lots[0]
            m = min(q, lq)
            closed.append({"buy_date": ld, "sell_date": t["Date"], "qty": m, "buy_price": lp, "sell_price": float(t["Price"])})
            q -= m
            lq -= m
            if lq <= 1e-9:
                lots.pop(0)
            else:
                lots[0][1] = lq
    return closed, lots


def cagr(entry, exit_, days):
    if not entry or days is None or days < 30 or exit_ is None:
        return None
    return (exit_ / entry) ** (365.0 / days) - 1


def buy_style(price, high52):
    if not high52 or high52 <= 0:
        return None
    r = price / high52
    if r < 0.85:
        return "Buys dips"
    if r > 0.97:
        return "Buys strength"
    return "Buys mid-range"


def horizon(days):
    if days is None:
        return None
    if days < 90:
        return "Short-term"
    if days <= 365:
        return "Medium-term"
    return "Long-term"


def main():
    deals = pd.read_csv(DATA / "deals.csv", parse_dates=["Date"])
    prices = pd.read_csv(DATA / "prices.csv", parse_dates=["Date"])
    overrides = load_overrides()
    asof = max(deals["Date"].max(), prices["Date"].max())

    # 52-week high per symbol per date (trailing 252 trading days).
    prices = prices.sort_values(["Symbol", "Date"])
    prices["High52"] = prices.groupby("Symbol")["Close"].transform(lambda s: s.rolling(252, min_periods=20).max())
    last_close = prices.sort_values("Date").groupby("Symbol").tail(1).set_index("Symbol")["Close"].to_dict()
    price_lookup = {(r.Symbol, r.Date): r for r in prices.itertuples()}

    deals = deals.sort_values("Date")
    clients = {}
    for (client, symbol), grp in deals.groupby(["Client", "Symbol"]):
        closed, open_lots = fifo_round_trips(grp)
        c = clients.setdefault(client, {"name": client, "type": classify(client, overrides),
                                        "positions": [], "round_trips": [], "trades": []})
        for t in grp.itertuples():
            pr = price_lookup.get((symbol, t.Date))
            c["trades"].append({"date": t.Date.strftime("%Y-%m-%d"), "symbol": symbol, "side": t.Side,
                                "qty": float(t.Qty), "price": float(t.Price), "value": float(t.Qty * t.Price),
                                "kind": t.DealKind,
                                "style": buy_style(float(t.Price), getattr(pr, "High52", None)) if (t.Side == "BUY" and pr) else None})
        for rt in closed:
            days = (rt["sell_date"] - rt["buy_date"]).days
            c["round_trips"].append({"symbol": symbol, "buy_date": rt["buy_date"].strftime("%Y-%m-%d"),
                                     "sell_date": rt["sell_date"].strftime("%Y-%m-%d"), "qty": rt["qty"],
                                     "buy_price": rt["buy_price"], "sell_price": rt["sell_price"], "days": days,
                                     "cagr": cagr(rt["buy_price"], rt["sell_price"], days)})
        open_qty = sum(l[1] for l in open_lots)
        if open_qty > 1e-9:
            cost = sum(l[1] * l[2] for l in open_lots) / open_qty
            first = min(l[0] for l in open_lots)
            days = (asof - first).days
            cur = float(last_close.get(symbol, cost))
            c["positions"].append({"symbol": symbol, "qty": open_qty, "avg_cost": cost, "current_price": cur,
                                   "invested": open_qty * cost, "current_value": open_qty * cur,
                                   "unrealised_pct": cur / cost - 1, "first_buy": first.strftime("%Y-%m-%d"),
                                   "days_held": days, "cagr": cagr(cost, cur, days)})

    # Derived style and summary per client
    for c in clients.values():
        held = [rt for rt in c["round_trips"]]
        days_w = [(rt["days"], rt["qty"]) for rt in held]
        avg_days = (sum(d * q for d, q in days_w) / sum(q for _, q in days_w)) if days_w else None
        if avg_days is None and c["positions"]:
            avg_days = sum(p["days_held"] for p in c["positions"]) / len(c["positions"])
        styles = [t["style"] for t in c["trades"] if t["style"]]
        c["summary"] = {
            "stocks": len({t["symbol"] for t in c["trades"]}),
            "buy_value": sum(t["value"] for t in c["trades"] if t["side"] == "BUY"),
            "sell_value": sum(t["value"] for t in c["trades"] if t["side"] == "SELL"),
            "current_value": sum(p["current_value"] for p in c["positions"]),
            "avg_holding_days": avg_days,
            "horizon": horizon(avg_days),
            "buy_style": max(set(styles), key=styles.count) if styles else None,
            "median_cagr": statistics.median([x for x in [p["cagr"] for p in c["positions"]] + [rt["cagr"] for rt in held] if x is not None]) if (c["positions"] or held) and any(x is not None for x in [p["cagr"] for p in c["positions"]] + [rt["cagr"] for rt in held]) else None,
        }
        c["summary"]["concentration"] = "Concentrated (1-2 stocks)" if c["summary"]["stocks"] <= 2 else ("Focused (3-4)" if c["summary"]["stocks"] <= 4 else "Diversified (5+)")

    # Investor-type aggregates ("common things")
    by_type = defaultdict(list)
    for c in clients.values():
        by_type[c["type"]].append(c)
    types = []
    for t, cs in sorted(by_type.items(), key=lambda kv: -sum(x["summary"]["buy_value"] for x in kv[1])):
        days = [x["summary"]["avg_holding_days"] for x in cs if x["summary"]["avg_holding_days"]]
        cg = [x["summary"]["median_cagr"] for x in cs if x["summary"]["median_cagr"] is not None]
        stock_count = defaultdict(float)
        for x in cs:
            for tr in x["trades"]:
                if tr["side"] == "BUY":
                    stock_count[tr["symbol"]] += tr["value"]
        dip = sum(1 for x in cs if x["summary"]["buy_style"] == "Buys dips")
        types.append({"type": t, "clients": len(cs),
                      "buy_value": sum(x["summary"]["buy_value"] for x in cs),
                      "current_value": sum(x["summary"]["current_value"] for x in cs),
                      "median_holding_days": statistics.median(days) if days else None,
                      "median_cagr": statistics.median(cg) if cg else None,
                      "pct_dip_buyers": dip / len(cs) if cs else None,
                      "top_stocks": sorted(stock_count, key=stock_count.get, reverse=True)[:5]})

    # Company view
    companies = []
    holdings_path = DATA / "holdings.csv"
    holdings = pd.read_csv(holdings_path).to_dict("records") if holdings_path.exists() else []
    for sym in sorted(deals["Symbol"].unique()):
        d = deals[deals["Symbol"] == sym]
        buyers = d[d["Side"] == "BUY"].groupby("Client")["Qty"].sum().sort_values(ascending=False).head(10)
        sellers = d[d["Side"] == "SELL"].groupby("Client")["Qty"].sum().sort_values(ascending=False).head(10)
        companies.append({"symbol": sym, "last_price": float(last_close.get(sym, 0) or 0),
                          "deal_count": int(len(d)),
                          "buy_value_by_type": {k: float(v) for k, v in d[d["Side"] == "BUY"].assign(
                              T=lambda x: x["Client"].map(lambda n: classify(n, overrides)),
                              V=lambda x: x["Qty"] * x["Price"]).groupby("T")["V"].sum().items()},
                          "top_buyers": list(buyers.index), "top_sellers": list(sellers.index)})

    result = {"as_of": asof.strftime("%Y-%m-%d"), "companies": companies, "types": types,
              "clients": sorted(clients.values(), key=lambda c: -c["summary"]["buy_value"]),
              "holdings": holdings}
    OUT.mkdir(exist_ok=True)
    (OUT / "data.json").write_text(json.dumps(result, default=str), encoding="utf-8")
    print(f"Wrote {OUT / 'data.json'}: {len(clients)} investors, {len(companies)} companies, {len(holdings)} holding rows")


if __name__ == "__main__":
    main()

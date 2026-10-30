# Investor Profiler

Daily dashboard of who owns and trades each tracked company: FII/FPI, mutual funds, insurers,
banks, AIFs and individuals. Shows amounts bought, when, holding period, CAGR and buying style.

**Dashboard:** published on GitHub Pages (link under the repository's Settings → Pages).

## How it works
1. Every weekday at about 8:30 PM IST, GitHub Actions runs `run_all.py`.
2. It downloads NSE bulk and block deals and daily prices (Yahoo Finance) for the companies in `config.py`.
3. It rebuilds the dashboard and saves it to `docs/index.html`, which GitHub Pages serves.

## Adding companies
Edit `COMPANIES` in `config.py`, then commit.

## Shareholding patterns (quarterly, manual)
Upload the filled NSE/BSE shareholding Excel file for each company and quarter into `data/shareholding/`
(GitHub: Add file → Upload files). The next daily run includes them.

## Run it yourself (optional)
    pip install pandas openpyxl requests yfinance
    python run_all.py

## Limits
- Bulk and block deals show only large trades. Smaller buys and sells are not visible.
- Mutual fund and FPI positions are only partly visible from deals.
- Investing style and holding period are estimates from trading behaviour.
- Investor type is set from names by rule. Overrides go in `data/client_types_override.csv` (columns `Client,Type`).
- Data is public NSE and Yahoo data, shown for information only.

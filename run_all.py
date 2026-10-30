"""Run the full pipeline. Steps 1-2 need internet; steps 3-5 work offline.
    python run_all.py              # full run
    python run_all.py --offline    # skip fetching, rebuild from data/ files you already have
"""
import sys
import fetch_deals, fetch_prices, parse_shareholding, analyse, build_dashboard

if "--offline" not in sys.argv:
    fetch_deals.main()
    fetch_prices.main()
parse_shareholding.main()
analyse.main()
build_dashboard.main()

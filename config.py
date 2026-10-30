"""Settings for the Investor Profiler. Edit the lists here."""
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = BASE / "output"

# NSE symbols you track (no .NS suffix)
COMPANIES = ["RELIANCE", "HDFCBANK", "INFY"]

# Deals and prices are pulled from this date onwards
START_DATE = "2023-01-01"

# Investor-type rules, checked top to bottom. First match wins.
# Add a row to client_types_override.csv to force any client into a type.
TYPE_RULES = [
    ("Mutual Fund", r"mutual fund|asset management|\bAMC\b|\bMF\b|nippon india|sbi funds|hdfc (mutual|amc)|icici prudential|kotak (mahindra )?(mf|mutual)|aditya birla sun life|\bUTI\b|axis (mf|mutual)|\bDSP\b|franklin|mirae|tata (mf|mutual)|motilal oswal (mf|mutual)|\bquant\b"),
    ("Insurance / Pension (DII)", r"\bLIC\b|life insurance|general insurance|insurance|pension|provident"),
    ("AIF / PE / VC", r"\bAIF\b|alternate investment|venture capital|private equity|\bPE\b fund"),
    ("Bank / NBFC (DII)", r"\bbank\b|\bNBFC\b|finance (ltd|limited)|financial services"),
    ("FII / FPI (Foreign)", r"\bFII\b|\bFPI\b|mauritius|singapore|cayman|ireland|luxembourg|offshore|overseas|\bglobal\b|\bfund\s+(lp|llc|plc)\b|\bpte\b|\bplc\b|\bcapital partners\b|\bgovernment of\b|\bsovereign\b|investment authority|\bgovernment\b|\bcentral bank\b"),
    ("Corporate / Other", r"\b(ltd|limited|llp|pvt|private|corp|inc|co)\b\.?"),
]

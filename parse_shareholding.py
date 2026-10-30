"""
Step 3: read exchange shareholding-pattern workbooks (.xlsx / .xlsm, the XBRL
template from NSE or BSE) and write one row per company, quarter and category.
Put the filled files in data/shareholding/ (one file per company per quarter).
Output: data/holdings.csv  columns: Symbol, Quarter, Category, Shares, Pct
"""
import re
from pathlib import Path
import openpyxl
import pandas as pd
from config import DATA

SRC = DATA / "shareholding"


def _first_text(cells):
    for c in cells:
        if isinstance(c, str) and c.strip() and not re.fullmatch(r"\(?[A-Za-z0-9]{1,4}\)?", c.strip()):
            return c.strip()
    return None


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _general_info(wb):
    """Return (symbol, quarter_label) from the GeneralInfo sheet, if present."""
    symbol, quarter = None, None
    if "GeneralInfo" not in wb.sheetnames:
        return symbol, quarter
    for row in wb["GeneralInfo"].iter_rows(values_only=True):
        cells = [c for c in row if c not in (None, "")]
        if len(cells) < 2:
            continue
        label = str(cells[0]).lower()
        value = str(cells[-1]).strip()
        if "nse symbol" in label and "regulation" not in value.lower():
            symbol = value
        if "quarter ended" in label and "regulation" not in value.lower():
            quarter = value
    return symbol, quarter


def parse_file(path: Path) -> pd.DataFrame:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    symbol, quarter = _general_info(wb)
    symbol = symbol or path.stem.split("_")[0].upper()
    quarter = quarter or "unknown"
    ws = wb["Shareholding Pattern"]
    rows = list(ws.iter_rows(values_only=True))

    # Find the header row and the two columns we need.
    col_shares = col_pct = header_idx = None
    for i, r in enumerate(rows[:15]):
        for j, c in enumerate(r):
            if isinstance(c, str):
                if col_shares is None and "total nos. shares" in c.lower():
                    col_shares, header_idx = j, i
                if col_pct is None and c.lower().startswith("shareholding as a %"):
                    col_pct = j
    if col_shares is None:
        raise ValueError(f"{path.name}: could not find the 'Total nos. shares' column")

    out, category = [], None
    for r in rows[header_idx + 1:]:
        label = _first_text(r[:4])
        if not label:
            continue
        shares = _num(r[col_shares]) if col_shares < len(r) else None
        pct = _num(r[col_pct]) if col_pct is not None and col_pct < len(r) else None
        if shares is None:
            # A heading line such as "(1) Institutions (Domestic)"
            if re.match(r"^(\(?\d\)|Table|Sub-Total)", label) is None:
                category = label
            continue
        name = label if not label.lower().startswith("sub-total") else label
        out.append({"Symbol": symbol.upper(), "Quarter": quarter, "Category": f"{category or ''} :: {name}".strip(" :"),
                    "Shares": shares, "Pct": pct})
    return pd.DataFrame(out)


def main():
    files = [p for p in SRC.glob("*") if p.suffix.lower() in (".xlsx", ".xlsm")] if SRC.exists() else []
    if not files:
        print(f"No shareholding files found in {SRC}. Add them and run again.")
        return
    frames = []
    for f in files:
        try:
            frames.append(parse_file(f))
            print(f"[ok] {f.name}")
        except Exception as exc:
            print(f"[skip] {f.name}: {exc}")
    if not frames:
        return
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(DATA / "holdings.csv", index=False)
    print(f"Saved {len(df)} holding rows to {DATA / 'holdings.csv'}")


if __name__ == "__main__":
    main()

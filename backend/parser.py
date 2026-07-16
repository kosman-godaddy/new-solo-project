import csv
import io
from datetime import datetime


def parse_csv(file_obj) -> list:
    reader = csv.DictReader(file_obj)
    headers = [h.lower().strip() for h in (reader.fieldnames or [])]

    if "transaction date" in headers or ("date" in headers and "description" in headers and "amount" in headers):
        return _parse_chase(reader)
    elif "posted date" in headers or "reference number" in headers:
        return _parse_bofa(reader)
    else:
        return _parse_generic(reader)


def _normalize_date(s: str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s}")


def _base_row() -> dict:
    return {"category": "Uncategorized", "is_recurring": False, "tags": []}


def _parse_chase(reader) -> list:
    rows = []
    for row in reader:
        row = {k.lower().strip(): v.strip() for k, v in row.items()}
        try:
            rows.append({
                **_base_row(),
                "date": _normalize_date(row.get("transaction date") or row["date"]),
                "description": row["description"],
                "amount": float(row["amount"].replace(",", "")),
            })
        except (ValueError, KeyError):
            continue
    return rows


def _parse_bofa(reader) -> list:
    rows = []
    for row in reader:
        row = {k.lower().strip(): v.strip() for k, v in row.items()}
        try:
            credits = float(row.get("credits", "") or 0)
            debits = float(row.get("debits", "") or 0)
            rows.append({
                **_base_row(),
                "date": _normalize_date(row.get("posted date") or row["date"]),
                "description": row["description"],
                "amount": credits - debits,
            })
        except (ValueError, KeyError):
            continue
    return rows


def _parse_generic(reader) -> list:
    rows = []
    for row in reader:
        row = {k.lower().strip(): v.strip() for k, v in row.items()}
        date_key = next((k for k in row if "date" in k), None)
        desc_key = next((k for k in row if any(x in k for x in ("desc", "memo", "name", "narr"))), None)
        amt_key = next((k for k in row if "amount" in k or "amt" in k), None)
        if not all([date_key, desc_key, amt_key]):
            continue
        try:
            rows.append({
                **_base_row(),
                "date": _normalize_date(row[date_key]),
                "description": row[desc_key],
                "amount": float(row[amt_key].replace(",", "")),
            })
        except (ValueError, KeyError):
            continue
    return rows

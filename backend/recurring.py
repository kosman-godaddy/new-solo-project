import re
from collections import defaultdict
from sqlalchemy.orm import Session
import models


def _normalize(description: str) -> str:
    s = description.lower()
    s = re.sub(r'\d+', '', s)
    s = re.sub(r'[^a-z\s]', '', s)
    return s.strip()


def _classify_interval(days: float) -> str | None:
    if 6 <= days <= 8:
        return "weekly"
    if 13 <= days <= 16:
        return "biweekly"
    if 28 <= days <= 32:
        return "monthly"
    if 360 <= days <= 370:
        return "annual"
    return None


def detect_recurring(db: Session):
    transactions = db.query(models.Transaction).order_by(models.Transaction.date).all()

    grouped = defaultdict(list)
    for t in transactions:
        grouped[_normalize(t.description)].append(t)

    for _, txns in grouped.items():
        if len(txns) < 2:
            continue

        txns.sort(key=lambda t: t.date)
        dates = [t.date for t in txns]
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        avg_interval = sum(intervals) / len(intervals)

        frequency = _classify_interval(avg_interval)
        if not frequency:
            continue

        amounts = [float(t.amount) for t in txns]
        if max(amounts) - min(amounts) > 1.00:
            continue

        for t in txns:
            t.is_recurring = True
            t.frequency = frequency
            tags = list(t.tags or [])
            if "subscription" not in tags:
                t.tags = tags + ["subscription"]

    db.commit()

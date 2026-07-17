import os
import anthropic
import models
from sqlalchemy.orm import Session

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CATEGORIES = [
    "Food & Dining", "Groceries", "Transport", "Subscriptions",
    "Shopping", "Health", "Utilities", "Travel", "Entertainment",
    "Income", "Transfers", "Uncategorized"
]

PROMPT = """You are a personal finance categorizer. Given a bank transaction description, return exactly one of these categories:

Food & Dining, Groceries, Transport, Subscriptions, Shopping, Health, Utilities, Travel, Entertainment, Income, Transfers, Uncategorized

Transaction description: "{description}"

Return only the category name, nothing else."""


def _call_claude(merchant: str) -> str:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=50,
            messages=[{"role": "user", "content": PROMPT.format(description=merchant)}]
        )
        category = response.content[0].text.strip()
        return category if category in CATEGORIES else "Uncategorized"
    except Exception as e:
        print(f"[categorizer error] {e}")
        return "Uncategorized"


def categorize_transactions(transactions: list, db: Session):
    for t in transactions:
        merchant = t["description"]
        cached = db.query(models.MerchantCache).filter_by(merchant=merchant).first()
        if cached:
            t["category"] = cached.category
        else:
            category = _call_claude(merchant)
            db.add(models.MerchantCache(merchant=merchant, category=category))
            db.commit()
            t["category"] = category

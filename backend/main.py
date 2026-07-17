import io
import csv
import uuid
from decimal import Decimal
from datetime import date, datetime

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import engine, get_db, Base
import models
from parser import parse_csv
from categorizer import categorize_transactions
from recurring import detect_recurring

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize(row) -> dict:
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif isinstance(val, (date, datetime)):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = float(val)
        result[col.name] = val
    return result


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    transactions = parse_csv(io.StringIO(content.decode("utf-8")))

    categorize_transactions(transactions, db)

    inserted = 0
    for t in transactions:
        exists = db.query(models.Transaction).filter_by(
            date=t["date"], description=t["description"], amount=t["amount"]
        ).first()
        if not exists:
            db.add(models.Transaction(**t))
            inserted += 1

    db.commit()
    detect_recurring(db)

    return {"inserted": inserted, "total": len(transactions)}


@app.get("/transactions")
def get_transactions(category: str = None, db: Session = Depends(get_db)):
    q = db.query(models.Transaction)
    if category:
        q = q.filter(models.Transaction.category == category)
    return [serialize(row) for row in q.order_by(models.Transaction.date.desc()).all()]


@app.put("/transactions/{id}")
def update_transaction(id: str, body: dict, db: Session = Depends(get_db)):
    t = db.query(models.Transaction).filter_by(id=id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    t.category = body["category"]
    db.commit()
    return {"ok": True}


@app.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Transaction.category, func.sum(models.Transaction.amount))
        .group_by(models.Transaction.category)
        .all()
    )
    return [{"category": r[0], "total": float(r[1])} for r in rows]


@app.get("/subscriptions")
def get_subscriptions(db: Session = Depends(get_db)):
    rows = db.query(models.Transaction).filter_by(is_recurring=True).all()
    return [serialize(row) for row in rows]


@app.get("/export")
def export_transactions(db: Session = Depends(get_db)):
    rows = db.query(models.Transaction).order_by(models.Transaction.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Amount"])
    for t in rows:
        writer.writerow([t.date.isoformat(), t.description, t.category, t.amount])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@app.delete("/transactions")
def clear_transactions(db: Session = Depends(get_db)):
    db.query(models.Transaction).delete()
    db.commit()
    return {"ok": True}

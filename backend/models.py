import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, Date, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(Text, default="Uncategorized")
    is_recurring = Column(Boolean, default=False)
    frequency = Column(Text, nullable=True)
    tags = Column(ARRAY(Text), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class MerchantCache(Base):
    __tablename__ = "merchant_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant = Column(Text, unique=True, nullable=False)
    category = Column(Text, nullable=False)

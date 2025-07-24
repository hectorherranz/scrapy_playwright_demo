 # scrapy_playwright_demo/items.py
from enum import Enum
from decimal import Decimal
from typing import Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from dataclasses import dataclass

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"

class ProductItem(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page: int
    title: str
    price_discounted: Decimal | None = None
    price_original: Decimal | None = None
    currency: Currency
    link: str
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # --- ensure Decimals even if floats slip in ---
    @field_validator("price_discounted", "price_original", mode="before")
    @classmethod
    def to_decimal(cls, v):
        if v is None:
            return v
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except Exception:
            return v

    # --- make sure JSON output is str for Decimal (safer) ---
    @field_serializer("price_discounted", "price_original", when_used="json")
    def serialize_decimal(self, v: Decimal | None):
        return str(v) if v is not None else None

@dataclass(slots=True)
class PageDone:
    page: int
    finished_at: str

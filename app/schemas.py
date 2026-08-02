from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=64)
    category: str = "Apparel"
    size: str | None = None
    color: str | None = None
    unit_price: Decimal = Field(ge=0)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0)
    stock_qty: int = Field(default=0, ge=0)
    low_stock_at: int = Field(default=5, ge=0)
    notes: str | None = None


class ProductOut(Orm):
    id: int
    name: str
    sku: str
    category: str
    size: str | None
    color: str | None
    unit_price: Decimal
    cost_price: Decimal
    stock_qty: int
    low_stock_at: int
    notes: str | None
    created_at: datetime


class SaleIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    note: str | None = None


class SaleOut(Orm):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    total: Decimal
    sold_at: datetime
    note: str | None
    product_name: str | None = None


class DashboardOut(BaseModel):
    product_count: int
    units_in_stock: int
    units_sold: int
    revenue: Decimal
    profit_estimate: Decimal
    sale_count: int
    low_stock: list[ProductOut]
    top_products: list[dict]
    recent_sales: list[SaleOut]

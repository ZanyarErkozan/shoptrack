from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=64)
    category: str = "Giyim"
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
    channel: str = "Magaza"
    commission_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    shipping_fee: Decimal = Field(default=Decimal("0"), ge=0)
    other_fee: Decimal = Field(default=Decimal("0"), ge=0)
    note: str | None = None
    unit_price: Decimal | None = None  # boşsa ürün fiyatı


class SaleOut(Orm):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: Decimal
    gross: Decimal
    cost_total: Decimal
    channel: str
    commission_pct: Decimal
    commission_amount: Decimal
    shipping_fee: Decimal
    other_fee: Decimal
    net_profit: Decimal
    margin_pct: Decimal = Decimal("0")
    status: str
    sold_at: datetime
    note: str | None


class ExpenseIn(BaseModel):
    title: str
    category: str = "Genel"
    amount: Decimal = Field(gt=0)
    spent_on: date | None = None
    note: str | None = None


class ExpenseOut(Orm):
    id: int
    title: str
    category: str
    amount: Decimal
    spent_on: date
    note: str | None
    created_at: datetime


class PurchaseIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    supplier: str | None = None
    note: str | None = None
    update_product_cost: bool = True


class PurchaseOut(Orm):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_cost: Decimal
    total_cost: Decimal
    supplier: str | None
    purchased_at: datetime
    note: str | None


class DayCloseIn(BaseModel):
    close_date: date | None = None
    note: str | None = None


class DayCloseOut(Orm):
    id: int
    close_date: date
    order_count: int
    gross: Decimal
    net_profit: Decimal
    expenses: Decimal
    result: Decimal
    note: str | None
    created_at: datetime


class PriceSimIn(BaseModel):
    unit_cost: Decimal = Field(ge=0)
    commission_pct: Decimal = Field(default=Decimal("15"), ge=0, le=100)
    shipping_per_unit: Decimal = Field(default=Decimal("0"), ge=0)
    other_per_unit: Decimal = Field(default=Decimal("0"), ge=0)
    target_margin_pct: Decimal = Field(default=Decimal("25"), ge=0, le=99)


class PriceSimOut(BaseModel):
    suggested_price: Decimal
    unit_cost: Decimal
    commission_pct: Decimal
    estimated_net: Decimal
    estimated_margin_pct: Decimal


class DashboardOut(BaseModel):
    period: str
    gross: Decimal
    net_profit: Decimal
    expenses: Decimal
    period_result: Decimal
    margin_pct: Decimal
    order_count: int
    units_sold: int
    product_count: int
    units_in_stock: int
    returned_count: int
    daily_trend: list[dict]
    top_products: list[dict]
    low_stock: list[ProductOut]
    recent_sales: list[SaleOut]
    alerts: list[dict]

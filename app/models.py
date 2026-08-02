from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(80), default="Genel")
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_at: Mapped[int] = mapped_column(Integer, default=5)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sales: Mapped[list["Sale"]] = relationship(back_populates="product")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="product")


class Sale(Base):
    """Sipariş satırı — kanal + kesintilerle net kâr tutulur."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gross: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # ciro
    cost_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    channel: Mapped[str] = mapped_column(String(32), default="Magaza")  # Magaza|Pazaryeri|Diger
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed|returned
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    product: Mapped[Product] = relationship(back_populates="sales")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), default="Genel")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    spent_on: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    supplier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    product: Mapped[Product] = relationship(back_populates="purchases")


class DayClose(Base):
    __tablename__ = "day_closes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    close_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    net_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    expenses: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    result: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))  # net - expenses
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import DayClose, Expense, Product, Purchase, Sale
from app.pricing import calc_line_economics, suggest_price
from app.schemas import (
    DashboardOut,
    DayCloseIn,
    DayCloseOut,
    ExpenseIn,
    ExpenseOut,
    PriceSimIn,
    PriceSimOut,
    ProductIn,
    ProductOut,
    PurchaseIn,
    PurchaseOut,
    SaleIn,
    SaleOut,
)

router = APIRouter(prefix="/api")

CHANNELS = {"Magaza", "Pazaryeri", "Diger"}


def _margin(gross: Decimal, net: Decimal) -> Decimal:
    if gross <= 0:
        return Decimal("0")
    return (net / gross * Decimal("100")).quantize(Decimal("0.01"))


def _sale_out(s: Sale) -> SaleOut:
    return SaleOut(
        id=s.id,
        product_id=s.product_id,
        product_name=s.product.name if s.product else None,
        quantity=s.quantity,
        unit_price=s.unit_price,
        gross=s.gross,
        cost_total=s.cost_total,
        channel=s.channel,
        commission_pct=s.commission_pct,
        commission_amount=s.commission_amount,
        shipping_fee=s.shipping_fee,
        other_fee=s.other_fee,
        net_profit=s.net_profit,
        margin_pct=_margin(s.gross, s.net_profit),
        status=s.status,
        sold_at=s.sold_at,
        note=s.note,
    )


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    # SQLite + naive datetimes — keep everything UTC-naive for reliable filters
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = today - timedelta(days=today.weekday())
    elif period == "today":
        start = today
    else:  # month
        start = today.replace(day=1)
    return start, now


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day)
    return start, start + timedelta(days=1)


# ---------- dashboard ----------


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(period: str = Query(default="month", pattern="^(today|week|month)$"), db: Session = Depends(get_db)):
    start, end = _period_bounds(period)
    products = list(db.scalars(select(Product).order_by(Product.name)).all())

    sales = list(
        db.scalars(
            select(Sale)
            .options(joinedload(Sale.product))
            .where(Sale.sold_at >= start, Sale.sold_at <= end, Sale.status == "completed")
        ).unique()
    )
    returned = db.scalar(
        select(func.count(Sale.id)).where(
            Sale.sold_at >= start, Sale.sold_at <= end, Sale.status == "returned"
        )
    ) or 0

    gross = sum((s.gross for s in sales), Decimal("0"))
    net = sum((s.net_profit for s in sales), Decimal("0"))
    units = sum(s.quantity for s in sales)

    exp_start = start.date()
    expenses_total = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.spent_on >= exp_start, Expense.spent_on <= end.date()
        )
    ) or Decimal("0")
    expenses_total = Decimal(str(expenses_total))
    period_result = (net - expenses_total).quantize(Decimal("0.01"))

    # daily trend last 14 days
    trend_start = (datetime.utcnow() - timedelta(days=13)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    trend_sales = list(
        db.scalars(
            select(Sale).where(Sale.sold_at >= trend_start, Sale.status == "completed")
        ).all()
    )
    by_day: dict[str, dict] = {}
    for i in range(14):
        d = (trend_start + timedelta(days=i)).date().isoformat()
        by_day[d] = {"date": d, "gross": 0.0, "net": 0.0, "orders": 0}
    for s in trend_sales:
        d = s.sold_at.date().isoformat()
        if d in by_day:
            by_day[d]["gross"] += float(s.gross)
            by_day[d]["net"] += float(s.net_profit)
            by_day[d]["orders"] += 1
    daily_trend = list(by_day.values())

    top_map: dict[int, dict] = {}
    for s in sales:
        row = top_map.setdefault(
            s.product_id,
            {"name": s.product.name if s.product else f"#{s.product_id}", "units": 0, "gross": 0.0, "net": 0.0},
        )
        row["units"] += s.quantity
        row["gross"] += float(s.gross)
        row["net"] += float(s.net_profit)
    top_products = sorted(top_map.values(), key=lambda x: x["net"], reverse=True)[:5]
    for t in top_products:
        t["margin_pct"] = round((t["net"] / t["gross"] * 100) if t["gross"] else 0, 2)

    low_stock = [p for p in products if p.stock_qty <= p.low_stock_at]

    recent = list(
        db.scalars(
            select(Sale).options(joinedload(Sale.product)).order_by(Sale.id.desc()).limit(10)
        ).unique()
    )

    alerts: list[dict] = []
    for p in low_stock:
        alerts.append(
            {"type": "stock", "level": "warn", "message": f"Düşük stok: {p.name} ({p.stock_qty} adet)"}
        )
    for s in sales:
        m = _margin(s.gross, s.net_profit)
        if m < 10:
            alerts.append(
                {
                    "type": "margin",
                    "level": "danger" if m < 0 else "warn",
                    "message": f"Düşük marjlı satış #{s.id}: %{m} ({s.product.name if s.product else s.product_id})",
                }
            )
    alerts = alerts[:12]

    return DashboardOut(
        period=period,
        gross=gross.quantize(Decimal("0.01")),
        net_profit=net.quantize(Decimal("0.01")),
        expenses=expenses_total.quantize(Decimal("0.01")),
        period_result=period_result,
        margin_pct=_margin(gross, net),
        order_count=len(sales),
        units_sold=units,
        product_count=len(products),
        units_in_stock=sum(p.stock_qty for p in products),
        returned_count=int(returned),
        daily_trend=daily_trend,
        top_products=top_products,
        low_stock=low_stock,
        recent_sales=[_sale_out(s) for s in recent],
        alerts=alerts,
    )


# ---------- products ----------


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), q: str | None = None):
    stmt = select(Product).order_by(Product.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Product.name.ilike(like)) | (Product.sku.ilike(like)))
    return list(db.scalars(stmt).all())


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    sku = body.sku.strip().upper()
    if db.scalar(select(Product).where(Product.sku == sku)):
        raise HTTPException(409, "SKU zaten var")
    p = Product(**{**body.model_dump(), "sku": sku, "name": body.name.strip()})
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductIn, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "ürün yok")
    sku = body.sku.strip().upper()
    if db.scalar(select(Product).where(Product.sku == sku, Product.id != product_id)):
        raise HTTPException(409, "SKU zaten var")
    data = body.model_dump()
    data["sku"] = sku
    data["name"] = body.name.strip()
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "ürün yok")
    if db.scalar(select(func.count(Sale.id)).where(Sale.product_id == product_id)):
        raise HTTPException(400, "satışı olan ürün silinemez")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------- sales / orders ----------


@router.get("/sales", response_model=list[SaleOut])
def list_sales(
    db: Session = Depends(get_db),
    status: str | None = None,
    limit: int = Query(default=100, le=500),
):
    stmt = select(Sale).options(joinedload(Sale.product)).order_by(Sale.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(Sale.status == status)
    return [_sale_out(s) for s in db.scalars(stmt).unique().all()]


@router.post("/sales", response_model=SaleOut, status_code=201)
def create_sale(body: SaleIn, db: Session = Depends(get_db)):
    if body.channel not in CHANNELS:
        raise HTTPException(400, "kanal: Magaza | Pazaryeri | Diger")
    p = db.get(Product, body.product_id)
    if not p:
        raise HTTPException(404, "ürün yok")
    if p.stock_qty < body.quantity:
        raise HTTPException(409, f"yetersiz stok ({p.stock_qty})")

    price = body.unit_price if body.unit_price is not None else p.unit_price
    eco = calc_line_economics(
        quantity=body.quantity,
        unit_price=price,
        unit_cost=p.cost_price,
        commission_pct=body.commission_pct,
        shipping_fee=body.shipping_fee,
        other_fee=body.other_fee,
    )
    sale = Sale(
        product_id=p.id,
        quantity=body.quantity,
        unit_price=price,
        gross=eco["gross"],
        cost_total=eco["cost_total"],
        channel=body.channel,
        commission_pct=body.commission_pct,
        commission_amount=eco["commission_amount"],
        shipping_fee=eco["shipping_fee"],
        other_fee=eco["other_fee"],
        net_profit=eco["net_profit"],
        status="completed",
        note=body.note,
    )
    p.stock_qty -= body.quantity
    db.add(sale)
    db.commit()
    sale = db.scalar(select(Sale).options(joinedload(Sale.product)).where(Sale.id == sale.id))
    return _sale_out(sale)


@router.post("/sales/{sale_id}/return", response_model=SaleOut)
def return_sale(sale_id: int, db: Session = Depends(get_db)):
    s = db.scalar(select(Sale).options(joinedload(Sale.product)).where(Sale.id == sale_id))
    if not s:
        raise HTTPException(404, "sipariş yok")
    if s.status == "returned":
        raise HTTPException(400, "zaten iade edilmiş")
    s.status = "returned"
    if s.product:
        s.product.stock_qty += s.quantity
    # net sıfırlama iade sonrası raporlarda completed filtresiyle düşer
    db.commit()
    db.refresh(s)
    return _sale_out(s)


# ---------- product analysis ----------


@router.get("/analysis/products")
def product_analysis(
    period: str = Query(default="month", pattern="^(today|week|month)$"),
    db: Session = Depends(get_db),
):
    start, end = _period_bounds(period)
    sales = list(
        db.scalars(
            select(Sale)
            .options(joinedload(Sale.product))
            .where(Sale.sold_at >= start, Sale.sold_at <= end, Sale.status == "completed")
        ).unique()
    )
    agg: dict[int, dict] = {}
    for s in sales:
        row = agg.setdefault(
            s.product_id,
            {
                "product_id": s.product_id,
                "name": s.product.name if s.product else f"#{s.product_id}",
                "sku": s.product.sku if s.product else "",
                "units": 0,
                "gross": Decimal("0"),
                "net": Decimal("0"),
                "commission": Decimal("0"),
                "orders": 0,
            },
        )
        row["units"] += s.quantity
        row["gross"] += s.gross
        row["net"] += s.net_profit
        row["commission"] += s.commission_amount
        row["orders"] += 1
    out = []
    for row in agg.values():
        g, n = row["gross"], row["net"]
        out.append(
            {
                **row,
                "gross": float(g),
                "net": float(n),
                "commission": float(row["commission"]),
                "margin_pct": float(_margin(g, n)),
            }
        )
    out.sort(key=lambda x: x["net"], reverse=True)
    return out


# ---------- expenses ----------


@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db)):
    return list(db.scalars(select(Expense).order_by(Expense.spent_on.desc(), Expense.id.desc()).limit(200)).all())


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseIn, db: Session = Depends(get_db)):
    e = Expense(
        title=body.title.strip(),
        category=body.category.strip() or "Genel",
        amount=body.amount,
        spent_on=body.spent_on or date.today(),
        note=body.note,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    e = db.get(Expense, expense_id)
    if not e:
        raise HTTPException(404, "gider yok")
    db.delete(e)
    db.commit()
    return {"ok": True}


# ---------- purchases ----------


@router.get("/purchases", response_model=list[PurchaseOut])
def list_purchases(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Purchase).options(joinedload(Purchase.product)).order_by(Purchase.id.desc()).limit(100)
    ).unique().all()
    return [
        PurchaseOut(
            id=r.id,
            product_id=r.product_id,
            product_name=r.product.name if r.product else None,
            quantity=r.quantity,
            unit_cost=r.unit_cost,
            total_cost=r.total_cost,
            supplier=r.supplier,
            purchased_at=r.purchased_at,
            note=r.note,
        )
        for r in rows
    ]


@router.post("/purchases", response_model=PurchaseOut, status_code=201)
def create_purchase(body: PurchaseIn, db: Session = Depends(get_db)):
    p = db.get(Product, body.product_id)
    if not p:
        raise HTTPException(404, "ürün yok")
    total = (body.unit_cost * body.quantity).quantize(Decimal("0.01"))
    # weighted avg cost
    if body.update_product_cost:
        old_qty = p.stock_qty
        old_val = p.cost_price * old_qty
        new_val = body.unit_cost * body.quantity
        new_qty = old_qty + body.quantity
        if new_qty > 0:
            p.cost_price = ((old_val + new_val) / Decimal(new_qty)).quantize(Decimal("0.01"))
    p.stock_qty += body.quantity
    row = Purchase(
        product_id=p.id,
        quantity=body.quantity,
        unit_cost=body.unit_cost,
        total_cost=total,
        supplier=body.supplier,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PurchaseOut(
        id=row.id,
        product_id=row.product_id,
        product_name=p.name,
        quantity=row.quantity,
        unit_cost=row.unit_cost,
        total_cost=row.total_cost,
        supplier=row.supplier,
        purchased_at=row.purchased_at,
        note=row.note,
    )


# ---------- price simulator ----------


@router.post("/tools/price-sim", response_model=PriceSimOut)
def price_sim(body: PriceSimIn):
    try:
        price = suggest_price(
            unit_cost=body.unit_cost,
            commission_pct=body.commission_pct,
            shipping_per_unit=body.shipping_per_unit,
            other_per_unit=body.other_per_unit,
            target_margin_pct=body.target_margin_pct,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    eco = calc_line_economics(
        quantity=1,
        unit_price=price,
        unit_cost=body.unit_cost,
        commission_pct=body.commission_pct,
        shipping_fee=body.shipping_per_unit,
        other_fee=body.other_per_unit,
    )
    return PriceSimOut(
        suggested_price=price,
        unit_cost=body.unit_cost,
        commission_pct=body.commission_pct,
        estimated_net=eco["net_profit"],
        estimated_margin_pct=eco["margin_pct"],
    )


# ---------- day close ----------


@router.get("/day-closes", response_model=list[DayCloseOut])
def list_day_closes(db: Session = Depends(get_db)):
    return list(db.scalars(select(DayClose).order_by(DayClose.close_date.desc()).limit(60)).all())


@router.post("/day-closes", response_model=DayCloseOut, status_code=201)
def create_day_close(body: DayCloseIn, db: Session = Depends(get_db)):
    d = body.close_date or date.today()
    if db.scalar(select(DayClose).where(DayClose.close_date == d)):
        raise HTTPException(409, "bu gün zaten kapatılmış")

    start, end = _day_bounds(d)
    sales = list(
        db.scalars(
            select(Sale).where(Sale.sold_at >= start, Sale.sold_at < end, Sale.status == "completed")
        ).all()
    )
    gross = sum((s.gross for s in sales), Decimal("0"))
    net = sum((s.net_profit for s in sales), Decimal("0"))
    expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.spent_on == d)
    ) or Decimal("0")
    expenses = Decimal(str(expenses))
    row = DayClose(
        close_date=d,
        order_count=len(sales),
        gross=gross.quantize(Decimal("0.01")),
        net_profit=net.quantize(Decimal("0.01")),
        expenses=expenses.quantize(Decimal("0.01")),
        result=(net - expenses).quantize(Decimal("0.01")),
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------- alerts shortcut ----------


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)):
    dash = dashboard(period="month", db=db)
    return dash.alerts

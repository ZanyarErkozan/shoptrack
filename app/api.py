from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Product, Sale
from app.schemas import DashboardOut, ProductIn, ProductOut, SaleIn, SaleOut

router = APIRouter(prefix="/api")


def _sale_out(s: Sale) -> SaleOut:
    return SaleOut(
        id=s.id,
        product_id=s.product_id,
        quantity=s.quantity,
        unit_price=s.unit_price,
        total=s.total,
        sold_at=s.sold_at,
        note=s.note,
        product_name=s.product.name if s.product else None,
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    products = list(db.scalars(select(Product).order_by(Product.name)).all())
    product_count = len(products)
    units_in_stock = sum(p.stock_qty for p in products)

    units_sold = db.scalar(select(func.coalesce(func.sum(Sale.quantity), 0))) or 0
    revenue = db.scalar(select(func.coalesce(func.sum(Sale.total), 0))) or Decimal("0")
    sale_count = db.scalar(select(func.count(Sale.id))) or 0

    # rough profit: sale total - cost * qty
    profit = Decimal("0")
    for s in db.scalars(select(Sale).options(joinedload(Sale.product))).unique():
        cost = (s.product.cost_price if s.product else Decimal("0")) * s.quantity
        profit += s.total - cost

    low_stock = [p for p in products if p.stock_qty <= p.low_stock_at]

    top_rows = db.execute(
        select(Product.name, func.sum(Sale.quantity).label("qty"), func.sum(Sale.total).label("rev"))
        .join(Sale, Sale.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(Sale.total).desc())
        .limit(5)
    ).all()
    top_products = [{"name": r[0], "units": int(r[1] or 0), "revenue": float(r[2] or 0)} for r in top_rows]

    recent = db.scalars(
        select(Sale).options(joinedload(Sale.product)).order_by(Sale.id.desc()).limit(8)
    ).unique().all()

    return DashboardOut(
        product_count=product_count,
        units_in_stock=int(units_in_stock),
        units_sold=int(units_sold),
        revenue=Decimal(str(revenue)),
        profit_estimate=profit.quantize(Decimal("0.01")),
        sale_count=int(sale_count),
        low_stock=low_stock,
        top_products=top_products,
        recent_sales=[_sale_out(s) for s in recent],
    )


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
        raise HTTPException(409, "SKU already exists")
    p = Product(**{**body.model_dump(), "sku": sku, "name": body.name.strip()})
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductIn, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "product not found")
    sku = body.sku.strip().upper()
    clash = db.scalar(select(Product).where(Product.sku == sku, Product.id != product_id))
    if clash:
        raise HTTPException(409, "SKU already exists")
    for k, v in body.model_dump().items():
        setattr(p, k, v.strip() if isinstance(v, str) and k in ("name", "sku") else v)
    p.sku = sku
    db.commit()
    db.refresh(p)
    return p


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "product not found")
    if db.scalar(select(func.count(Sale.id)).where(Sale.product_id == product_id)):
        raise HTTPException(400, "product has sales — delete sales first or keep it")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.get("/sales", response_model=list[SaleOut])
def list_sales(db: Session = Depends(get_db), limit: int = 100):
    rows = db.scalars(
        select(Sale).options(joinedload(Sale.product)).order_by(Sale.id.desc()).limit(limit)
    ).unique().all()
    return [_sale_out(s) for s in rows]


@router.post("/sales", response_model=SaleOut, status_code=201)
def create_sale(body: SaleIn, db: Session = Depends(get_db)):
    p = db.get(Product, body.product_id)
    if not p:
        raise HTTPException(404, "product not found")
    if p.stock_qty < body.quantity:
        raise HTTPException(409, f"not enough stock (have {p.stock_qty})")

    total = (p.unit_price * body.quantity).quantize(Decimal("0.01"))
    sale = Sale(
        product_id=p.id,
        quantity=body.quantity,
        unit_price=p.unit_price,
        total=total,
        note=body.note,
    )
    p.stock_qty -= body.quantity
    db.add(sale)
    db.commit()
    db.refresh(sale)
    sale = db.scalar(select(Sale).options(joinedload(Sale.product)).where(Sale.id == sale.id))
    return _sale_out(sale)


@router.delete("/sales/{sale_id}")
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    """Undo a sale — stock goes back."""
    s = db.get(Sale, sale_id)
    if not s:
        raise HTTPException(404, "sale not found")
    p = db.get(Product, s.product_id)
    if p:
        p.stock_qty += s.quantity
    db.delete(s)
    db.commit()
    return {"ok": True}

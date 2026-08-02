"""Demo tişört mağazası — panel boş gelmesin diye."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from app.db import SessionLocal, init_db
from app.models import Expense, Product, Sale
from app.pricing import calc_line_economics


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Product).first():
            print("seed atlandı — veri var")
            return

        catalog = [
            Product(
                name="Klasik Tişört — Siyah",
                sku="TEE-BLK-M",
                category="Tişört",
                size="M",
                color="Siyah",
                unit_price=Decimal("349.90"),
                cost_price=Decimal("120.00"),
                stock_qty=48,
            ),
            Product(
                name="Klasik Tişört — Beyaz",
                sku="TEE-WHT-M",
                category="Tişört",
                size="M",
                color="Beyaz",
                unit_price=Decimal("349.90"),
                cost_price=Decimal("120.00"),
                stock_qty=40,
            ),
            Product(
                name="Oversize Hoodie",
                sku="HD-GRY-L",
                category="Sweatshirt",
                size="L",
                color="Gri",
                unit_price=Decimal("899.00"),
                cost_price=Decimal("380.00"),
                stock_qty=14,
                low_stock_at=4,
            ),
            Product(
                name="Logo Şapka",
                sku="CAP-NVY",
                category="Aksesuar",
                color="Lacivert",
                unit_price=Decimal("249.00"),
                cost_price=Decimal("90.00"),
                stock_qty=25,
            ),
            Product(
                name="Basic Tee — Olive",
                sku="TEE-OLV-S",
                category="Tişört",
                size="S",
                color="Haki",
                unit_price=Decimal("329.00"),
                cost_price=Decimal("115.00"),
                stock_qty=3,
                low_stock_at=5,
            ),
        ]
        db.add_all(catalog)
        db.flush()

        now = datetime.utcnow()
        samples = [
            (catalog[0], 2, "Magaza", Decimal("0"), Decimal("0"), Decimal("0"), 5),
            (catalog[1], 1, "Magaza", Decimal("0"), Decimal("0"), Decimal("0"), 10),
            (catalog[3], 3, "Magaza", Decimal("0"), Decimal("0"), Decimal("0"), 18),
            (catalog[0], 3, "Pazaryeri", Decimal("15"), Decimal("45"), Decimal("0"), 28),
            (catalog[2], 1, "Pazaryeri", Decimal("18"), Decimal("55"), Decimal("10"), 36),
            (catalog[1], 2, "Pazaryeri", Decimal("15"), Decimal("45"), Decimal("0"), 48),
            (catalog[3], 2, "Pazaryeri", Decimal("15"), Decimal("35"), Decimal("0"), 60),
            (catalog[4], 1, "Pazaryeri", Decimal("15"), Decimal("40"), Decimal("0"), 8),
        ]
        for p, qty, channel, comm, ship, other, hours_ago in samples:
            eco = calc_line_economics(
                quantity=qty,
                unit_price=p.unit_price,
                unit_cost=p.cost_price,
                commission_pct=comm,
                shipping_fee=ship,
                other_fee=other,
            )
            db.add(
                Sale(
                    product_id=p.id,
                    quantity=qty,
                    unit_price=p.unit_price,
                    gross=eco["gross"],
                    cost_total=eco["cost_total"],
                    channel=channel,
                    commission_pct=comm,
                    commission_amount=eco["commission_amount"],
                    shipping_fee=eco["shipping_fee"],
                    other_fee=eco["other_fee"],
                    net_profit=eco["net_profit"],
                    status="completed",
                    sold_at=now - timedelta(hours=hours_ago),
                )
            )
            p.stock_qty -= qty

        db.add_all(
            [
                Expense(
                    title="Dükkan kirası",
                    category="Kira",
                    amount=Decimal("18000"),
                    spent_on=date.today().replace(day=1),
                ),
                Expense(
                    title="Instagram reklam",
                    category="Reklam",
                    amount=Decimal("2500"),
                    spent_on=date.today() - timedelta(days=2),
                ),
                Expense(
                    title="Kargo poşeti / koli",
                    category="Operasyon",
                    amount=Decimal("420"),
                    spent_on=date.today() - timedelta(days=1),
                ),
            ]
        )
        db.commit()
        print("seed tamam — Vitrin demo verisi yüklendi")
    finally:
        db.close()


if __name__ == "__main__":
    main()

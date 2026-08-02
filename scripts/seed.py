"""Seed a small tee shop so the UI isn't empty on first launch."""

from decimal import Decimal

from app.db import SessionLocal, init_db
from app.models import Product


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Product).first():
            print("seed skipped — products already exist")
            return

        samples = [
            Product(
                name="Classic Tee — Black",
                sku="TEE-BLK-M",
                category="T-Shirts",
                size="M",
                color="Black",
                unit_price=Decimal("349.90"),
                cost_price=Decimal("120.00"),
                stock_qty=40,
            ),
            Product(
                name="Classic Tee — White",
                sku="TEE-WHT-M",
                category="T-Shirts",
                size="M",
                color="White",
                unit_price=Decimal("349.90"),
                cost_price=Decimal("120.00"),
                stock_qty=35,
            ),
            Product(
                name="Oversized Hoodie",
                sku="HD-GRY-L",
                category="Hoodies",
                size="L",
                color="Grey",
                unit_price=Decimal("899.00"),
                cost_price=Decimal("380.00"),
                stock_qty=12,
                low_stock_at=4,
            ),
            Product(
                name="Cap — Logo",
                sku="CAP-NVY",
                category="Accessories",
                color="Navy",
                unit_price=Decimal("249.00"),
                cost_price=Decimal("90.00"),
                stock_qty=22,
            ),
        ]
        db.add_all(samples)
        db.commit()
        print("seed ok — sample tee shop catalog loaded")
    finally:
        db.close()


if __name__ == "__main__":
    main()

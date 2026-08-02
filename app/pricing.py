from decimal import Decimal


def calc_line_economics(
    *,
    quantity: int,
    unit_price: Decimal,
    unit_cost: Decimal,
    commission_pct: Decimal = Decimal("0"),
    shipping_fee: Decimal = Decimal("0"),
    other_fee: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    """Ciro / maliyet / komisyon / net kâr — sipariş satırı motoru."""
    qty = Decimal(quantity)
    gross = (unit_price * qty).quantize(Decimal("0.01"))
    cost_total = (unit_cost * qty).quantize(Decimal("0.01"))
    commission_amount = (gross * (commission_pct / Decimal("100"))).quantize(Decimal("0.01"))
    shipping = Decimal(shipping_fee).quantize(Decimal("0.01"))
    other = Decimal(other_fee).quantize(Decimal("0.01"))
    net = (gross - cost_total - commission_amount - shipping - other).quantize(Decimal("0.01"))
    margin = Decimal("0")
    if gross > 0:
        margin = (net / gross * Decimal("100")).quantize(Decimal("0.01"))
    return {
        "gross": gross,
        "cost_total": cost_total,
        "commission_amount": commission_amount,
        "shipping_fee": shipping,
        "other_fee": other,
        "net_profit": net,
        "margin_pct": margin,
    }


def suggest_price(
    *,
    unit_cost: Decimal,
    commission_pct: Decimal,
    shipping_per_unit: Decimal,
    other_per_unit: Decimal,
    target_margin_pct: Decimal,
) -> Decimal:
    """
    Hedef net marja göre önerilen satış fiyatı.
    net = P - cost - P*comm% - ship - other
    margin = net/P => P = (cost + ship + other) / (1 - comm% - margin%)
    """
    denom = Decimal("1") - (commission_pct / Decimal("100")) - (target_margin_pct / Decimal("100"))
    if denom <= 0:
        raise ValueError("Komisyon + hedef marj 100%'ü aşamaz")
    base = unit_cost + shipping_per_unit + other_per_unit
    return (base / denom).quantize(Decimal("0.01"))

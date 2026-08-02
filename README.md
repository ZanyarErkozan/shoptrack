# Vitrin (ShopTrack)

Local store control panel for revenue, **net profit**, commissions, returns, expenses, and product profitability.

Runs on your PC (`start.bat`), opens in the browser, and works on your phone on the same Wi‑Fi. Data stays in a SQLite file — no cloud account required.

Inspired by panels like Cironet, but offline-first and built for a small shop (tees, accessories, multi-channel sales).

## Screenshots

### Dashboard
![Dashboard — revenue, net profit, trend chart](docs/screenshots/dashboard.png)

### Orders
![Orders — channel, commission, shipping fees](docs/screenshots/orders.png)

### Product analysis
![Product analysis — gross / net / margin by SKU](docs/screenshots/analysis.png)

## How it works

```
Browser (PC or phone)
        │
        ▼
   FastAPI  (:7070)
        │
   net-profit engine   (gross − cost − commission − shipping − other)
        │
        ▼
   SQLite  (shoptrack.db)
```

1. You add **products** (price, cost, stock).
2. You record an **order** with a channel (`Magaza` / `Pazaryeri` / `Diger`), commission %, and fees.
3. Vitrin stores the line economics and updates stock.
4. The **dashboard** aggregates ciro (gross), net profit, margin, expenses, and period result (`net − expenses`).
5. **Returns** restock the item and exclude the sale from completed totals.
6. **Purchases** add stock and refresh average cost. **Day close** locks a day’s summary.

UI language is Turkish (shop-floor friendly). Code / README are English.

### Net profit formula

```
net = gross − product_cost − commission − shipping_fee − other_fee
margin% = net / gross × 100
```

## Marketplace API (ready to plug in)

Today you enter marketplace fees by hand. The REST API is already the integration surface:

- `GET /api/dashboard` — period KPIs + daily trend  
- `GET|POST /api/sales` — orders with channel / commission / net  
- `POST /api/sales/{id}/return` — returns  
- `GET /api/analysis/products` — per-SKU profitability  
- `GET|POST /api/expenses`, `/api/purchases`, `/api/day-closes`  
- `POST /api/tools/price-sim` — price suggestion for a target margin  

**If you connect an external marketplace API** (e.g. Trendyol seller API), a sync job can pull orders, commissions, and settlements into these same endpoints / tables — the panel would then show live data without manual entry. That connector is not bundled yet; the data model and routes are shaped so it can drop in later.

## Modules

| Panel | What it does |
|---|---|
| Kontrol Paneli | Revenue, net, expenses, period result, chart, alerts |
| Siparişler | Create orders with fees; list + return |
| Ürünler | Catalog CRUD + stock |
| Ürün Analizi | Gross / net / margin by product |
| İadeler | Returned orders |
| Giderler | Rent, ads, ops costs |
| Satın Alma | Restock + weighted average cost |
| Kâr Hesaplama | Price simulator (target margin) |
| Uyarılar | Low stock / low margin |
| Gün Sonu | Lock daily cash summary |

## Run (Windows)

Double-click `start.bat`.

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# if you had an older DB schema:
del shoptrack.db
python -m scripts.seed

uvicorn app.main:app --host 0.0.0.0 --port 7070
```

- PC: http://127.0.0.1:7070  
- Phone: http://`<your-pc-lan-ip>`:7070 (same Wi‑Fi). Check IP with `ipconfig`.

Leave the terminal open while you use the app.

## Stack

FastAPI · SQLAlchemy · SQLite · Chart.js · vanilla JS panel

## License

Use it, fork it, change it.

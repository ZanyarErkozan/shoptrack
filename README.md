# ShopTrack

Local store tracker for product stock, sales, and revenue.
Built for a small shop (tees, hoodies, accessories…) — runs on your PC,
opens in the browser, works on your phone on the same Wi‑Fi.

**Stack:** FastAPI · SQLite · plain HTML/CSS/JS

## What you get

- **Overview** — revenue, units sold, product count, estimated profit, low stock, top sellers
- **Products** — add / edit / delete catalog (SKU, size, color, price, cost, stock)
- **Sales** — record a sale, stock drops automatically, undo restocks

Data lives in `shoptrack.db` next to the app. No cloud account.

## Run on Windows

Double-click `start.bat`.

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.seed
uvicorn app.main:app --host 0.0.0.0 --port 7070
```

- PC: http://127.0.0.1:7070  
- Phone: http://`<your-pc-ip>`:7070 (same Wi‑Fi)

Find your PC IP: `ipconfig` → IPv4 Address.

## Notes

- Currency defaults to TRY (`app/config.py` / env).
- Closing the terminal stops the app. Leave `start.bat` open to keep it running.
- First launch seeds a tiny sample tee catalog so the screen isn’t empty.

## License

Use it, fork it, change it — no ceremony.

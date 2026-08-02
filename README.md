# Vitrin (ShopTrack)

Cironet tarzı **yerel** mağaza paneli — ciro, net kâr, komisyon, iade, gider,
ürün analizi. Bulut yok; SQLite dosyanda durur. PC’de çalışır, aynı Wi‑Fi’deki
telefonda tarayıcıdan açılır.

## Modüller

- Kontrol paneli (ciro / net / marj / gider / dönem sonucu + günlük trend)
- Siparişler (Mağaza / Pazaryeri / Diğer + komisyon & kargo)
- Ürünler, ürün analizi, iadeler
- Giderler, satın alma (stok + ortalama maliyet)
- Kâr hesaplama (hedef marja göre fiyat önerisi)
- Uyarılar, gün sonu kasa

Net kâr: `ciro − maliyet − komisyon − kargo − diğer`

## Çalıştır (Windows)

`start.bat` dosyasına çift tıkla.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# eski db şeması bozulduysa:
del shoptrack.db
python -m scripts.seed
uvicorn app.main:app --host 0.0.0.0 --port 7070
```

- PC: http://127.0.0.1:7070  
- Telefon: http://`<PC-IP>`:7070

## Not

Trendyol API bağlantısı yok — pazaryeri kesintilerini sen girersin.
Bu bilinçli: kurulum basit, veri sende kalır.

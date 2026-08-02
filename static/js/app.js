const currency = (window.VITRIN && window.VITRIN.currency) || "TRY";
let period = "month";
let trendChart = null;

const TITLES = {
  dash: ["Kontrol Paneli", "Ciro, net kâr ve sipariş özeti"],
  orders: ["Siparişler", "Kanal, komisyon ve net kâr ile satış kaydı"],
  products: ["Ürünler", "Katalog, stok ve maliyet"],
  analysis: ["Ürün Analizi", "Ürün bazlı ciro / net / marj"],
  returns: ["İadeler", "İade edilen siparişler"],
  expenses: ["Giderler", "Kira, reklam ve operasyon giderleri"],
  purchases: ["Satın Alma", "Tedarik ve stok girişi"],
  calc: ["Kâr Hesaplama", "Hedef marja göre fiyat önerisi"],
  alerts: ["Uyarılar", "Düşük stok ve düşük marj"],
  dayclose: ["Gün Sonu", "Günlük kasa kapanışı"],
};

const money = (n) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(n || 0));

const toast = (msg) => {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.hidden = true), 2400);
};

const esc = (s) =>
  String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let detail = "İstek başarısız";
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

function setView(name) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  const [t, s] = TITLES[name] || ["Vitrin", ""];
  document.getElementById("pageTitle").textContent = t;
  document.getElementById("pageSub").textContent = s;
  document.getElementById("periodSwitch").style.display = ["dash", "analysis"].includes(name) ? "flex" : "none";
  closeSidebar();
  loadView(name).catch((e) => toast(e.message));
}

async function loadView(name) {
  if (name === "dash") return loadDashboard();
  if (name === "orders") return Promise.all([fillProductSelects(), loadOrders()]);
  if (name === "products") return loadProducts();
  if (name === "analysis") return loadAnalysis();
  if (name === "returns") return loadReturns();
  if (name === "expenses") return loadExpenses();
  if (name === "purchases") return Promise.all([fillProductSelects(), loadPurchases()]);
  if (name === "alerts") return loadAlerts();
  if (name === "dayclose") return loadDayCloses();
}

document.querySelectorAll(".nav-item").forEach((btn) => btn.addEventListener("click", () => setView(btn.dataset.view)));

document.getElementById("periodSwitch").addEventListener("click", (e) => {
  const b = e.target.closest("[data-period]");
  if (!b) return;
  period = b.dataset.period;
  document.querySelectorAll("#periodSwitch button").forEach((x) => x.classList.toggle("on", x === b));
  const active = document.querySelector(".nav-item.active")?.dataset.view || "dash";
  loadView(active).catch((err) => toast(err.message));
});

function openSidebar() {
  document.getElementById("sidebar").classList.add("open");
  document.getElementById("backdrop").hidden = false;
}
function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("backdrop").hidden = true;
}
document.getElementById("menuBtn").addEventListener("click", openSidebar);
document.getElementById("backdrop").addEventListener("click", closeSidebar);

async function loadDashboard() {
  const d = await api(`/api/dashboard?period=${period}`);
  document.getElementById("kpiGrid").innerHTML = `
    <div class="kpi"><span>Ciro</span><strong>${money(d.gross)}</strong><em>${d.order_count} sipariş</em></div>
    <div class="kpi"><span>Net Kâr</span><strong>${money(d.net_profit)}</strong><em>marj %${d.margin_pct}</em></div>
    <div class="kpi"><span>Giderler</span><strong>${money(d.expenses)}</strong><em>dönem içi</em></div>
    <div class="kpi"><span>Dönem Sonucu</span><strong>${money(d.period_result)}</strong><em>net − gider</em></div>
  `;

  renderAlerts(document.getElementById("dashAlerts"), d.alerts);
  document.getElementById("topProducts").innerHTML = d.top_products.length
    ? d.top_products
        .map(
          (p) => `<div class="row"><div><div>${esc(p.name)}</div><div class="meta">${p.units} adet · marj %${p.margin_pct}</div></div>
          <div class="right">${money(p.net)}<div class="meta">ciro ${money(p.gross)}</div></div></div>`
        )
        .join("")
    : `<p class="empty">Henüz satış yok.</p>`;

  document.getElementById("recentSales").innerHTML = d.recent_sales.length
    ? d.recent_sales.map(orderRow).join("")
    : `<p class="empty">Kayıt yok.</p>`;

  const ctx = document.getElementById("trendChart");
  const labels = d.daily_trend.map((x) => x.date.slice(5));
  const gross = d.daily_trend.map((x) => x.gross);
  const net = d.daily_trend.map((x) => x.net);
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Ciro",
          data: gross,
          borderColor: "#5b8cff",
          backgroundColor: "rgba(91,140,255,0.15)",
          tension: 0.35,
          fill: true,
        },
        {
          label: "Net",
          data: net,
          borderColor: "#3dd6c6",
          backgroundColor: "transparent",
          tension: 0.35,
        },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#8b9bb8" } } },
      scales: {
        x: { ticks: { color: "#8b9bb8" }, grid: { color: "rgba(255,255,255,0.04)" } },
        y: { ticks: { color: "#8b9bb8" }, grid: { color: "rgba(255,255,255,0.04)" } },
      },
    },
  });
}

function renderAlerts(el, alerts) {
  el.innerHTML = alerts?.length
    ? alerts
        .map(
          (a) =>
            `<div class="row"><div><span class="badge ${a.level === "danger" ? "danger" : "warn"}">${esc(
              a.type
            )}</span><div class="meta" style="margin-top:.4rem">${esc(a.message)}</div></div></div>`
        )
        .join("")
    : `<p class="empty">Uyarı yok — güzel.</p>`;
}

function orderRow(s) {
  const badge =
    s.status === "returned"
      ? `<span class="badge danger">iade</span>`
      : `<span class="badge ok">${esc(s.channel)}</span>`;
  const actions =
    s.status === "completed"
      ? `<div class="actions-inline"><button class="btn tiny danger" data-return="${s.id}" type="button">İade</button></div>`
      : "";
  return `<div class="row">
    <div>
      <div>${esc(s.product_name || "#" + s.product_id)} ${badge}</div>
      <div class="meta">×${s.quantity} · kom %${s.commission_pct} · ${new Date(s.sold_at).toLocaleString("tr-TR")}</div>
    </div>
    <div class="right">
      <div>${money(s.gross)}</div>
      <div class="meta">net ${money(s.net_profit)} · %${s.margin_pct}</div>
      ${actions}
    </div>
  </div>`;
}

async function fillProductSelects() {
  const products = await api("/api/products");
  const opts = products
    .map((p) => `<option value="${p.id}">${esc(p.name)} (stok ${p.stock_qty}) — ${money(p.unit_price)}</option>`)
    .join("");
  document.getElementById("sProduct").innerHTML = opts;
  document.getElementById("bProduct").innerHTML = opts;
}

async function loadOrders() {
  const sales = await api("/api/sales?status=completed");
  document.getElementById("ordersList").innerHTML = sales.length
    ? sales.map(orderRow).join("")
    : `<p class="empty">Sipariş yok.</p>`;
}

async function loadReturns() {
  const sales = await api("/api/sales?status=returned");
  document.getElementById("returnsList").innerHTML = sales.length
    ? sales.map(orderRow).join("")
    : `<p class="empty">İade yok.</p>`;
}

document.getElementById("sChannel").addEventListener("change", (e) => {
  if (e.target.value === "Magaza") {
    document.getElementById("sComm").value = 0;
    document.getElementById("sShip").value = 0;
  } else if (e.target.value === "Pazaryeri") {
    document.getElementById("sComm").value = 15;
    document.getElementById("sShip").value = 45;
  }
});

document.getElementById("saleForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/sales", {
      method: "POST",
      body: JSON.stringify({
        product_id: Number(document.getElementById("sProduct").value),
        quantity: Number(document.getElementById("sQty").value),
        channel: document.getElementById("sChannel").value,
        commission_pct: document.getElementById("sComm").value,
        shipping_fee: document.getElementById("sShip").value,
        other_fee: document.getElementById("sOther").value,
        note: document.getElementById("sNote").value || null,
      }),
    });
    toast("Sipariş kaydedildi");
    document.getElementById("sQty").value = 1;
    await Promise.all([loadOrders(), fillProductSelects()]);
  } catch (err) {
    toast(err.message);
  }
});

document.body.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-return]");
  if (!btn) return;
  if (!confirm("Bu siparişi iade et (stok geri gelsin)?")) return;
  try {
    await api(`/api/sales/${btn.dataset.return}/return`, { method: "POST" });
    toast("İade alındı");
    const view = document.querySelector(".nav-item.active")?.dataset.view;
    await loadView(view || "orders");
  } catch (err) {
    toast(err.message);
  }
});

function resetProductForm() {
  document.getElementById("productForm").reset();
  document.getElementById("productId").value = "";
  document.getElementById("productFormTitle").textContent = "Ürün ekle";
  document.getElementById("productSubmit").textContent = "Kaydet";
  document.getElementById("productCancel").hidden = true;
  document.getElementById("pCategory").value = "Tişört";
  document.getElementById("pLow").value = 5;
}

async function loadProducts(q = "") {
  const products = await api("/api/products" + (q ? `?q=${encodeURIComponent(q)}` : ""));
  document.getElementById("productList").innerHTML = products.length
    ? products
        .map(
          (p) => `<div class="row">
        <div>
          <div>${esc(p.name)} ${p.stock_qty <= p.low_stock_at ? '<span class="badge warn">düşük</span>' : ""}</div>
          <div class="meta">${esc(p.sku)} · ${esc(p.category)} · stok ${p.stock_qty} · maliyet ${money(p.cost_price)}</div>
        </div>
        <div class="right">
          <div>${money(p.unit_price)}</div>
          <div class="actions-inline">
            <button class="btn tiny" type="button" data-edit='${encodeURIComponent(JSON.stringify(p))}'>Düzenle</button>
            <button class="btn tiny danger" type="button" data-del="${p.id}">Sil</button>
          </div>
        </div>
      </div>`
        )
        .join("")
    : `<p class="empty">Ürün yok.</p>`;
}

document.getElementById("productForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("productId").value;
  const body = {
    name: document.getElementById("pName").value,
    sku: document.getElementById("pSku").value,
    category: document.getElementById("pCategory").value || "Genel",
    size: document.getElementById("pSize").value || null,
    color: document.getElementById("pColor").value || null,
    unit_price: document.getElementById("pPrice").value,
    cost_price: document.getElementById("pCost").value || 0,
    stock_qty: Number(document.getElementById("pStock").value || 0),
    low_stock_at: Number(document.getElementById("pLow").value || 0),
  };
  try {
    if (id) await api(`/api/products/${id}`, { method: "PUT", body: JSON.stringify(body) });
    else await api("/api/products", { method: "POST", body: JSON.stringify(body) });
    toast(id ? "Ürün güncellendi" : "Ürün eklendi");
    resetProductForm();
    await loadProducts(document.getElementById("productSearch").value.trim());
  } catch (err) {
    toast(err.message);
  }
});

document.getElementById("productCancel").addEventListener("click", resetProductForm);

document.getElementById("productList").addEventListener("click", async (e) => {
  const edit = e.target.closest("[data-edit]");
  const del = e.target.closest("[data-del]");
  if (edit) {
    const p = JSON.parse(decodeURIComponent(edit.dataset.edit));
    document.getElementById("productId").value = p.id;
    document.getElementById("pName").value = p.name;
    document.getElementById("pSku").value = p.sku;
    document.getElementById("pCategory").value = p.category || "";
    document.getElementById("pSize").value = p.size || "";
    document.getElementById("pColor").value = p.color || "";
    document.getElementById("pPrice").value = p.unit_price;
    document.getElementById("pCost").value = p.cost_price;
    document.getElementById("pStock").value = p.stock_qty;
    document.getElementById("pLow").value = p.low_stock_at;
    document.getElementById("productFormTitle").textContent = "Ürün düzenle";
    document.getElementById("productSubmit").textContent = "Güncelle";
    document.getElementById("productCancel").hidden = false;
  }
  if (del) {
    if (!confirm("Ürünü sil?")) return;
    try {
      await api(`/api/products/${del.dataset.del}`, { method: "DELETE" });
      toast("Silindi");
      await loadProducts();
    } catch (err) {
      toast(err.message);
    }
  }
});

let searchT;
document.getElementById("productSearch").addEventListener("input", (e) => {
  clearTimeout(searchT);
  searchT = setTimeout(() => loadProducts(e.target.value.trim()), 200);
});

async function loadAnalysis() {
  const rows = await api(`/api/analysis/products?period=${period}`);
  document.getElementById("analysisList").innerHTML = rows.length
    ? rows
        .map(
          (r) => `<div class="row">
        <div><div>${esc(r.name)}</div><div class="meta">${esc(r.sku)} · ${r.orders} sipariş · ${r.units} adet</div></div>
        <div class="right">
          <div>net ${money(r.net)}</div>
          <div class="meta">ciro ${money(r.gross)} · marj %${r.margin_pct} · kom ${money(r.commission)}</div>
        </div>
      </div>`
        )
        .join("")
    : `<p class="empty">Bu dönemde satış yok.</p>`;
}

async function loadExpenses() {
  const rows = await api("/api/expenses");
  document.getElementById("expenseList").innerHTML = rows.length
    ? rows
        .map(
          (e) => `<div class="row">
        <div><div>${esc(e.title)}</div><div class="meta">${esc(e.category)} · ${e.spent_on}</div></div>
        <div class="right">
          <div>${money(e.amount)}</div>
          <div class="actions-inline"><button class="btn tiny danger" data-exp-del="${e.id}" type="button">Sil</button></div>
        </div>
      </div>`
        )
        .join("")
    : `<p class="empty">Gider yok.</p>`;
}

document.getElementById("expenseForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/expenses", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("eTitle").value,
        category: document.getElementById("eCat").value || "Genel",
        amount: document.getElementById("eAmount").value,
        spent_on: document.getElementById("eDate").value || null,
      }),
    });
    toast("Gider eklendi");
    e.target.reset();
    await loadExpenses();
  } catch (err) {
    toast(err.message);
  }
});

document.getElementById("expenseList").addEventListener("click", async (e) => {
  const b = e.target.closest("[data-exp-del]");
  if (!b) return;
  try {
    await api(`/api/expenses/${b.dataset.expDel}`, { method: "DELETE" });
    toast("Gider silindi");
    await loadExpenses();
  } catch (err) {
    toast(err.message);
  }
});

async function loadPurchases() {
  const rows = await api("/api/purchases");
  document.getElementById("purchaseList").innerHTML = rows.length
    ? rows
        .map(
          (r) => `<div class="row">
        <div><div>${esc(r.product_name || "#" + r.product_id)}</div>
        <div class="meta">×${r.quantity} · ${r.supplier || "tedarikçi yok"} · ${new Date(r.purchased_at).toLocaleString("tr-TR")}</div></div>
        <div class="right">${money(r.total_cost)}<div class="meta">${money(r.unit_cost)} / adet</div></div>
      </div>`
        )
        .join("")
    : `<p class="empty">Alım yok.</p>`;
}

document.getElementById("purchaseForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/purchases", {
      method: "POST",
      body: JSON.stringify({
        product_id: Number(document.getElementById("bProduct").value),
        quantity: Number(document.getElementById("bQty").value),
        unit_cost: document.getElementById("bCost").value,
        supplier: document.getElementById("bSupplier").value || null,
      }),
    });
    toast("Stok girildi");
    await Promise.all([loadPurchases(), fillProductSelects()]);
  } catch (err) {
    toast(err.message);
  }
});

document.getElementById("simForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await api("/api/tools/price-sim", {
      method: "POST",
      body: JSON.stringify({
        unit_cost: document.getElementById("simCost").value,
        commission_pct: document.getElementById("simComm").value,
        shipping_per_unit: document.getElementById("simShip").value,
        other_per_unit: document.getElementById("simOther").value,
        target_margin_pct: document.getElementById("simMargin").value,
      }),
    });
    const box = document.getElementById("simResult");
    box.hidden = false;
    box.innerHTML = `<div>Önerilen satış fiyatı</div><strong>${money(r.suggested_price)}</strong>
      <div class="meta">Tahmini net ${money(r.estimated_net)} · marj %${r.estimated_margin_pct}</div>`;
  } catch (err) {
    toast(err.message);
  }
});

async function loadAlerts() {
  const alerts = await api("/api/alerts");
  renderAlerts(document.getElementById("alertsList"), alerts);
}

async function loadDayCloses() {
  const rows = await api("/api/day-closes");
  document.getElementById("dayList").innerHTML = rows.length
    ? rows
        .map(
          (d) => `<div class="row">
        <div><div>${d.close_date}</div><div class="meta">${d.order_count} sipariş${d.note ? " · " + esc(d.note) : ""}</div></div>
        <div class="right">
          <div>sonuç ${money(d.result)}</div>
          <div class="meta">ciro ${money(d.gross)} · net ${money(d.net_profit)} · gider ${money(d.expenses)}</div>
        </div>
      </div>`
        )
        .join("")
    : `<p class="empty">Henüz gün kapanışı yok.</p>`;
}

document.getElementById("dayForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/day-closes", {
      method: "POST",
      body: JSON.stringify({
        close_date: document.getElementById("dDate").value || null,
        note: document.getElementById("dNote").value || null,
      }),
    });
    toast("Gün kapatıldı");
    await loadDayCloses();
  } catch (err) {
    toast(err.message);
  }
});

function showLan() {
  const host = location.hostname;
  const el = document.getElementById("lanHint");
  if (host === "127.0.0.1" || host === "localhost") {
    el.textContent = "Telefon: aynı Wi‑Fi’de bilgisayarın IP adresi + port 7070";
  } else {
    el.textContent = "Bağlantı: " + location.origin;
  }
}

document.getElementById("dDate").valueAsDate = new Date();
document.getElementById("eDate").valueAsDate = new Date();
showLan();
setView("dash");

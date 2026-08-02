const currency = (window.SHOPTRACK && window.SHOPTRACK.currency) || "TRY";

const money = (n) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency, maximumFractionDigits: 2 }).format(
    Number(n || 0)
  );

const toast = (msg) => {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 2200);
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

function setTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

async function loadDashboard() {
  const d = await api("/api/dashboard");
  document.getElementById("metrics").innerHTML = `
    <div class="metric"><span>Revenue</span><strong>${money(d.revenue)}</strong></div>
    <div class="metric"><span>Units sold</span><strong>${d.units_sold}</strong></div>
    <div class="metric"><span>Products</span><strong>${d.product_count}</strong></div>
    <div class="metric"><span>Est. profit</span><strong>${money(d.profit_estimate)}</strong></div>
  `;

  const top = document.getElementById("topProducts");
  top.innerHTML = d.top_products.length
    ? d.top_products
        .map(
          (p) => `
      <div class="row">
        <div>
          <div>${escapeHtml(p.name)}</div>
          <div class="meta">${p.units} sold</div>
        </div>
        <div class="right">${money(p.revenue)}</div>
      </div>`
        )
        .join("")
    : `<p class="empty">No sales yet — record one under Sales.</p>`;

  const low = document.getElementById("lowStock");
  low.innerHTML = d.low_stock.length
    ? d.low_stock
        .map(
          (p) => `
      <div class="row">
        <div>
          <div>${escapeHtml(p.name)}</div>
          <div class="meta">${escapeHtml(p.sku)}</div>
        </div>
        <div class="right"><span class="badge warn">${p.stock_qty} left</span></div>
      </div>`
        )
        .join("")
    : `<p class="empty">Stock levels look fine.</p>`;

  const recent = document.getElementById("recentSales");
  recent.innerHTML = d.recent_sales.length
    ? d.recent_sales.map(saleRow).join("")
    : `<p class="empty">Nothing sold yet.</p>`;
}

function saleRow(s) {
  return `
    <div class="row">
      <div>
        <div>${escapeHtml(s.product_name || "Product #" + s.product_id)}</div>
        <div class="meta">×${s.quantity} · ${new Date(s.sold_at).toLocaleString()}</div>
      </div>
      <div class="right">
        <div>${money(s.total)}</div>
        <div class="actions">
          <button class="btn tiny danger" data-undo="${s.id}" type="button">Undo</button>
        </div>
      </div>
    </div>`;
}

async function loadProducts(q = "") {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  const products = await api("/api/products" + qs);
  const box = document.getElementById("productList");
  box.innerHTML = products.length
    ? products
        .map(
          (p) => `
      <div class="row">
        <div>
          <div>${escapeHtml(p.name)} ${p.stock_qty <= p.low_stock_at ? '<span class="badge warn">low</span>' : ""}</div>
          <div class="meta">${escapeHtml(p.sku)} · ${escapeHtml(p.category)}${p.size ? " · " + escapeHtml(p.size) : ""} · stock ${p.stock_qty}</div>
        </div>
        <div class="right">
          <div>${money(p.unit_price)}</div>
          <div class="actions">
            <button class="btn tiny" data-edit='${encodeURIComponent(JSON.stringify(p))}' type="button">Edit</button>
            <button class="btn tiny danger" data-del="${p.id}" type="button">Delete</button>
          </div>
        </div>
      </div>`
        )
        .join("")
    : `<p class="empty">No products yet.</p>`;

  const select = document.getElementById("sProduct");
  const current = select.value;
  select.innerHTML = products
    .map((p) => `<option value="${p.id}">${escapeHtml(p.name)} (${p.stock_qty} in stock) — ${money(p.unit_price)}</option>`)
    .join("");
  if (current) select.value = current;
}

async function loadSales() {
  const sales = await api("/api/sales");
  document.getElementById("salesList").innerHTML = sales.length
    ? sales.map(saleRow).join("")
    : `<p class="empty">No sales recorded.</p>`;
}

function resetProductForm() {
  document.getElementById("productForm").reset();
  document.getElementById("productId").value = "";
  document.getElementById("productFormTitle").textContent = "Add product";
  document.getElementById("productSubmit").textContent = "Save product";
  document.getElementById("productCancel").hidden = true;
  document.getElementById("pCategory").value = "T-Shirts";
  document.getElementById("pLow").value = 5;
}

document.getElementById("productForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("productId").value;
  const body = {
    name: document.getElementById("pName").value,
    sku: document.getElementById("pSku").value,
    category: document.getElementById("pCategory").value || "General",
    size: document.getElementById("pSize").value || null,
    color: document.getElementById("pColor").value || null,
    unit_price: document.getElementById("pPrice").value,
    cost_price: document.getElementById("pCost").value || 0,
    stock_qty: Number(document.getElementById("pStock").value || 0),
    low_stock_at: Number(document.getElementById("pLow").value || 0),
  };
  try {
    if (id) {
      await api(`/api/products/${id}`, { method: "PUT", body: JSON.stringify(body) });
      toast("Product updated");
    } else {
      await api("/api/products", { method: "POST", body: JSON.stringify(body) });
      toast("Product added");
    }
    resetProductForm();
    await refreshAll();
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
    document.getElementById("productFormTitle").textContent = "Edit product";
    document.getElementById("productSubmit").textContent = "Update product";
    document.getElementById("productCancel").hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  if (del) {
    if (!confirm("Delete this product?")) return;
    try {
      await api(`/api/products/${del.dataset.del}`, { method: "DELETE" });
      toast("Product deleted");
      await refreshAll();
    } catch (err) {
      toast(err.message);
    }
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
        note: document.getElementById("sNote").value || null,
      }),
    });
    document.getElementById("sQty").value = 1;
    document.getElementById("sNote").value = "";
    toast("Sale recorded");
    await refreshAll();
    setTab("dash");
  } catch (err) {
    toast(err.message);
  }
});

async function onUndoClick(e) {
  const btn = e.target.closest("[data-undo]");
  if (!btn) return;
  if (!confirm("Undo this sale and restock?")) return;
  try {
    await api(`/api/sales/${btn.dataset.undo}`, { method: "DELETE" });
    toast("Sale undone");
    await refreshAll();
  } catch (err) {
    toast(err.message);
  }
}

document.getElementById("recentSales").addEventListener("click", onUndoClick);
document.getElementById("salesList").addEventListener("click", onUndoClick);

let searchTimer;
document.getElementById("productSearch").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadProducts(e.target.value.trim()), 200);
});

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadProducts(document.getElementById("productSearch").value.trim()), loadSales()]);
}

function showLanHint() {
  const host = location.hostname;
  const port = location.port || "7070";
  const el = document.getElementById("lanHint");
  if (host === "127.0.0.1" || host === "localhost") {
    el.textContent = "Phone tip: open this PC’s LAN IP on port " + port + " (same Wi‑Fi).";
  } else {
    el.textContent = "Connected at " + location.origin;
  }
}

showLanHint();
refreshAll().catch((err) => toast(err.message));

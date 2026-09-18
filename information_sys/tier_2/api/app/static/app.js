const state = { products: [], categories: [] };

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `Ошибка ${response.status}`;
    try { message = (await response.json()).detail || message; } catch (_) { /* no JSON */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function notify(message, error = false) {
  const notice = $("#notice");
  notice.textContent = message;
  notice.classList.toggle("error", error);
  notice.hidden = false;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => { notice.hidden = true; }, 4500);
}

async function loadStatus() {
  try {
    const status = await request("/api/status");
    setStatus(status.database);
  } catch (_) {
    setStatus({ available: false });
  }
}

function setStatus(data) {
  const element = $("#databaseStatus");
  element.className = `status-pill ${data.available ? "ok" : "down"}`;
  const state = data.available ? "доступна" : "недоступна";
  element.textContent = `DATABASE · ${state}`;
}

function fillSelects() {
  $("#productCategory").innerHTML = state.categories
    .map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
  $("#movementProduct").innerHTML = state.products
    .map((item) => `<option value="${item.id}">${escapeHtml(item.name)} · ${item.quantity} ${escapeHtml(item.unit)}</option>`).join("");
}

function renderProducts() {
  const body = $("#productsBody");
  if (!state.products.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">На складе пока нет товаров</td></tr>';
    return;
  }
  body.innerHTML = state.products.map((item) => `
    <tr>
      <td class="sku">${escapeHtml(item.sku)}</td>
      <td><strong>${escapeHtml(item.name)}</strong></td>
      <td>${escapeHtml(item.category)}</td>
      <td class="number"><span class="stock ${item.low_stock ? "low" : ""}">${item.quantity} <small>${escapeHtml(item.unit)}</small></span></td>
      <td class="number">${item.reorder_level}</td>
      <td><div class="row-actions">
        <button class="small-action" data-edit="${item.id}">Изменить</button>
        <button class="small-action danger" data-delete="${item.id}">Удалить</button>
      </div></td>
    </tr>`).join("");

  body.querySelectorAll("[data-edit]").forEach((button) => button.addEventListener("click", () => editProduct(Number(button.dataset.edit))));
  body.querySelectorAll("[data-delete]").forEach((button) => button.addEventListener("click", () => deleteProduct(Number(button.dataset.delete))));
}

function renderMetrics() {
  $("#productCount").textContent = state.products.length;
  $("#unitCount").textContent = state.products.reduce((sum, item) => sum + item.quantity, 0);
  $("#lowCount").textContent = state.products.filter((item) => item.low_stock).length;
}

async function loadMovements() {
  const items = await request("/api/movements?limit=12");
  const body = $("#movementsBody");
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="5" class="empty">Операций пока нет</td></tr>';
    return;
  }
  body.innerHTML = items.map((item) => {
    const inbound = item.movement_type === "in";
    return `<tr>
      <td>${new Date(item.created_at).toLocaleString("ru-RU")}</td>
      <td>${escapeHtml(item.product)}</td>
      <td class="operation ${item.movement_type}">${inbound ? "Приход" : "Списание"}</td>
      <td class="number">${inbound ? "+" : "−"}${item.quantity}</td>
      <td>${escapeHtml(item.note || "—")}</td>
    </tr>`;
  }).join("");
}

async function loadAll() {
  try {
    const [categories, products] = await Promise.all([
      request("/api/categories"),
      request("/api/products"),
    ]);
    state.categories = categories;
    state.products = products.items;
    renderProducts();
    renderMetrics();
    fillSelects();
    await loadMovements();
  } catch (error) {
    notify(error.message, true);
  }
  await loadStatus();
}

async function editProduct(id) {
  const item = state.products.find((product) => product.id === id);
  const name = prompt("Наименование товара", item.name);
  if (name === null || !name.trim()) return;
  const reorder = prompt("Минимальный запас", item.reorder_level);
  if (reorder === null || Number(reorder) < 0) return;
  try {
    await request(`/api/products/${id}`, {
      method: "PUT",
      body: JSON.stringify({ name: name.trim(), category_id: item.category_id, unit: item.unit, reorder_level: Number(reorder) }),
    });
    notify("Карточка товара обновлена");
    await loadAll();
  } catch (error) { notify(error.message, true); }
}

async function deleteProduct(id) {
  const item = state.products.find((product) => product.id === id);
  if (!confirm(`Удалить «${item.name}» вместе с историей операций?`)) return;
  try {
    await request(`/api/products/${id}`, { method: "DELETE" });
    notify("Товар удалён");
    await loadAll();
  } catch (error) { notify(error.message, true); }
}

$("#productForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.category_id = Number(payload.category_id);
  payload.quantity = Number(payload.quantity);
  payload.reorder_level = Number(payload.reorder_level);
  try {
    await request("/api/products", { method: "POST", body: JSON.stringify(payload) });
    $("#productDialog").close();
    event.currentTarget.reset();
    notify("Товар добавлен");
    await loadAll();
  } catch (error) { notify(error.message, true); }
});

$("#movementForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.product_id = Number(payload.product_id);
  payload.quantity = Number(payload.quantity);
  payload.note = payload.note || null;
  try {
    await request("/api/movements", { method: "POST", body: JSON.stringify(payload) });
    $("#movementDialog").close();
    event.currentTarget.reset();
    notify("Операция проведена");
    await loadAll();
  } catch (error) { notify(error.message, true); }
});

$("#addProductButton").addEventListener("click", () => $("#productDialog").showModal());
$("#addMovementButton").addEventListener("click", () => $("#movementDialog").showModal());
$("#refreshButton").addEventListener("click", loadAll);
document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});
$("#addCategoryButton").addEventListener("click", async () => {
  const name = prompt("Название новой категории");
  if (!name?.trim()) return;
  try {
    await request("/api/categories", { method: "POST", body: JSON.stringify({ name: name.trim() }) });
    notify("Категория добавлена");
    await loadAll();
  } catch (error) { notify(error.message, true); }
});

loadAll();
setInterval(loadStatus, 5000);

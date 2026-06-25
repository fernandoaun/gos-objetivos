(function () {
  "use strict";

  const API = window.CAP_API_BASE || "/gos/capacitacion/api";
  const MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
  ];
  const DOW = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

  let calYear = new Date().getFullYear();
  let calMonth = new Date().getMonth();
  let calView = "mes";
  let encuentros = [];
  let metaSectores = [];
  let metaPuestos = [];

  async function fetchJson(url, options) {
    const r = await fetch(url, { credentials: "same-origin", ...options });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = data.error || "Error de red";
      throw new Error(msg);
    }
    return data;
  }

  async function postJson(url, body) {
    return fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function isoDate(y, m, d) {
    return `${y}-${pad(m + 1)}-${pad(d)}`;
  }

  function lastDayOfMonth(y, m) {
    return new Date(y, m + 1, 0).getDate();
  }

  function togglePanel(panelId, show) {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.classList.toggle("cap-hidden", !show);
  }

  function setFormError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg || "";
  }

  function formToObject(form) {
    const data = {};
    new FormData(form).forEach((value, key) => {
      const v = String(value).trim();
      if (v !== "") data[key] = v;
    });
    return data;
  }

  function fillSelect(selectId, items, placeholder) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.codigo ? `${item.codigo} — ${item.nombre}` : item.nombre;
      sel.appendChild(opt);
    });
  }

  async function loadMeta() {
    const [sectores, puestos] = await Promise.all([
      fetchJson(`${API}/sectores`),
      fetchJson(`${API}/puestos`),
    ]);
    metaSectores = sectores.sectores || [];
    metaPuestos = puestos.puestos || [];
    fillSelect("cap-p-sector", metaSectores, "— Sin sector —");
    fillSelect("cap-p-puesto", metaPuestos, "— Sin puesto —");
  }

  function renderRecursos(data) {
    const tbody = document.getElementById("cap-recursos-body");
    if (!tbody) return;
    tbody.innerHTML = (data.recursos || []).map((r) => `
      <tr>
        <td>${r.nombre}</td>
        <td>
          <div class="cap-status-group">
            <span class="cap-badge cap-badge--green" title="Al día">${r.verde}</span>
            <span class="cap-badge cap-badge--red" title="Pendiente">${r.rojo}</span>
            <span class="cap-badge cap-badge--gray" title="Sin datos">${r.gris}</span>
          </div>
        </td>
      </tr>
    `).join("");

    const hab = document.getElementById("cap-habilitados-pct");
    const inh = document.getElementById("cap-inhabilitados-pct");
    if (hab) hab.textContent = `${data.habilitados_pct || 0}%`;
    if (inh) inh.textContent = `${data.inhabilitados_pct || 0}%`;
  }

  function encuentrosDelDia(y, m, d) {
    const key = isoDate(y, m, d);
    return encuentros.filter((e) => e.fecha === key);
  }

  function renderCalendario() {
    const label = document.getElementById("cap-cal-month-label");
    if (label) label.textContent = `${MESES[calMonth]} ${calYear}`;

    const grid = document.getElementById("cap-cal-grid");
    if (!grid) return;

    let html = DOW.map((d) => `<div class="cap-cal-dow">${d}</div>`).join("");

    const first = new Date(calYear, calMonth, 1);
    let startDow = first.getDay() - 1;
    if (startDow < 0) startDow = 6;

    const daysInMonth = lastDayOfMonth(calYear, calMonth);
    const prevMonth = calMonth === 0 ? 11 : calMonth - 1;
    const prevYear = calMonth === 0 ? calYear - 1 : calYear;
    const daysPrev = lastDayOfMonth(prevYear, prevMonth);

    const today = new Date();
    const isTodayMonth = today.getFullYear() === calYear && today.getMonth() === calMonth;

    for (let i = 0; i < startDow; i++) {
      const d = daysPrev - startDow + i + 1;
      html += `<div class="cap-cal-cell cap-cal-cell--muted"><span class="cap-cal-daynum">${d}</span></div>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const evs = encuentrosDelDia(calYear, calMonth, d);
      const todayCls = isTodayMonth && today.getDate() === d ? " cap-cal-cell--today" : "";
      const evHtml = evs
        .map(
          (e) =>
            `<span class="cap-cal-event${e.estado === "cancelado" ? " cap-cal-event--cancelado" : ""}" title="${e.titulo}">${e.titulo}</span>`
        )
        .join("");
      html += `<div class="cap-cal-cell${todayCls}"><span class="cap-cal-daynum">${d}</span>${evHtml}</div>`;
    }

    const totalCells = startDow + daysInMonth;
    const trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let d = 1; d <= trailing; d++) {
      html += `<div class="cap-cal-cell cap-cal-cell--muted"><span class="cap-cal-daynum">${d}</span></div>`;
    }

    grid.innerHTML = html;
  }

  async function loadEncuentros() {
    const desde = isoDate(calYear, calMonth, 1);
    const hasta = isoDate(calYear, calMonth, lastDayOfMonth(calYear, calMonth));
    const data = await fetchJson(`${API}/encuentros?desde=${desde}&hasta=${hasta}`);
    encuentros = data.encuentros || [];
    renderCalendario();
  }

  async function loadDashboard() {
    const data = await fetchJson(`${API}/dashboard`);
    renderRecursos(data);
  }

  function bindCalendar() {
    document.getElementById("cap-cal-prev")?.addEventListener("click", () => {
      calMonth -= 1;
      if (calMonth < 0) {
        calMonth = 11;
        calYear -= 1;
      }
      loadEncuentros();
    });
    document.getElementById("cap-cal-next")?.addEventListener("click", () => {
      calMonth += 1;
      if (calMonth > 11) {
        calMonth = 0;
        calYear += 1;
      }
      loadEncuentros();
    });
    document.querySelectorAll(".cap-cal-view-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".cap-cal-view-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        calView = btn.dataset.view;
        if (calView !== "mes") {
          alert("Vista semana/día próximamente. Por ahora se muestra el mes.");
        }
      });
    });
  }

  async function loadPersonas(selectId) {
    const list = document.getElementById("cap-personas-list");
    const detail = document.getElementById("cap-persona-detail");
    if (!list) return;

    list.innerHTML = '<li class="cap-loading">Cargando...</li>';
    const data = await fetchJson(`${API}/participantes`);
    const items = data.participantes || [];

    if (!items.length) {
      list.innerHTML = '<li class="cap-empty">Sin participantes cargados</li>';
      if (detail) detail.innerHTML = '<p class="cap-empty">Agregá personas para ver el analítico.</p>';
      return;
    }

    list.innerHTML = items
      .map(
        (p) =>
          `<li><button type="button" class="cap-list-item" data-id="${p.id}">${p.nombre}${p.legajo ? ` <span style="color:var(--cap-muted);font-size:.78rem">(${p.legajo})</span>` : ""}</button></li>`
      )
      .join("");

    list.querySelectorAll(".cap-list-item").forEach((btn) => {
      btn.addEventListener("click", () => selectPersona(btn.dataset.id, btn));
    });

    const targetId = selectId || items[0].id;
    const targetBtn = list.querySelector(`.cap-list-item[data-id="${targetId}"]`) || list.querySelector(".cap-list-item");
    selectPersona(targetId, targetBtn);
  }

  async function selectPersona(id, btn) {
    document.querySelectorAll(".cap-list-item").forEach((b) => b.classList.remove("active"));
    if (btn) btn.classList.add("active");

    const detail = document.getElementById("cap-persona-detail");
    if (!detail) return;
    detail.innerHTML = '<p class="cap-loading">Cargando analítico...</p>';

    const data = await fetchJson(`${API}/participantes/${id}/analitico`);
    const p = data.participante;

    detail.innerHTML = `
      <div class="cap-widget-head" style="border-bottom:1px solid var(--cap-border);margin:-1rem -1rem 1rem;padding:1rem;">
        <i class="bi bi-person-badge"></i>
        <div>
          <h2 class="cap-widget-title">${p.nombre}</h2>
          <div style="font-size:.8rem;color:var(--cap-muted)">
            ${p.sector_nombre || "—"} · ${p.puesto_nombre || "—"}
          </div>
        </div>
      </div>

      <div class="cap-analitico-section">
        <h3>Cursos realizados</h3>
        ${renderTable(
          ["Curso", "Fecha", "Nota"],
          (data.cursos_realizados || []).map((c) => [
            c.curso_nombre,
            c.fecha_realizacion,
            c.nota != null ? c.nota : "—",
          ])
        )}
      </div>

      <div class="cap-analitico-section">
        <h3>Pendientes</h3>
        ${renderTable(
          ["Nombre", "Tipo", "Origen"],
          (data.pendientes || []).map((x) => [x.nombre, x.tipo, x.origen_requisito])
        )}
      </div>

      <div class="cap-analitico-section">
        <h3>Planificación</h3>
        ${renderTable(
          ["Curso", "Fecha prevista", "Estado"],
          (data.planificacion || []).map((pl) => [
            pl.curso_nombre,
            pl.fecha_planificada || "—",
            pl.estado,
          ])
        )}
      </div>
    `;
  }

  function renderTable(headers, rows) {
    if (!rows.length) return '<p class="cap-empty" style="padding:.5rem">Sin registros</p>';
    return `<table class="cap-mini-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }

  async function loadCursos() {
    const tbody = document.getElementById("cap-cursos-body");
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4" class="cap-loading">Cargando...</td></tr>';
    const data = await fetchJson(`${API}/cursos`);
    const items = data.cursos || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="cap-empty">Sin cursos cargados</td></tr>';
      return;
    }
    tbody.innerHTML = items
      .map(
        (c) => `
      <tr>
        <td><strong>${c.codigo}</strong></td>
        <td>${c.nombre}</td>
        <td>${c.horas != null ? c.horas : "—"}</td>
        <td>${c.modalidad || "—"}</td>
      </tr>`
      )
      .join("");
  }

  async function loadPuestos() {
    const tbody = document.getElementById("cap-puestos-body");
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="2" class="cap-loading">Cargando...</td></tr>';
    const data = await fetchJson(`${API}/puestos`);
    const items = data.puestos || [];
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="2" class="cap-empty">Sin puestos cargados</td></tr>';
      return;
    }
    tbody.innerHTML = items
      .map((p) => `<tr><td><strong>${p.codigo}</strong></td><td>${p.nombre}</td></tr>`)
      .join("");
  }

  function bindPersonaForm() {
    const form = document.getElementById("cap-persona-form");
    if (!form) return;

    document.getElementById("cap-btn-nueva-persona")?.addEventListener("click", async () => {
      await loadMeta();
      form.reset();
      setFormError("cap-persona-form-error", "");
      togglePanel("cap-persona-form-panel", true);
      document.getElementById("cap-p-nombre")?.focus();
    });

    document.getElementById("cap-persona-cancel")?.addEventListener("click", () => {
      togglePanel("cap-persona-form-panel", false);
      setFormError("cap-persona-form-error", "");
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setFormError("cap-persona-form-error", "");
      const payload = formToObject(form);
      if (payload.sector_id) payload.sector_id = Number(payload.sector_id);
      if (payload.puesto_id) payload.puesto_id = Number(payload.puesto_id);
      try {
        const data = await postJson(`${API}/participantes`, payload);
        togglePanel("cap-persona-form-panel", false);
        form.reset();
        await loadPersonas(data.participante?.id);
      } catch (err) {
        setFormError("cap-persona-form-error", err.message);
      }
    });
  }

  function bindCursoForm() {
    const form = document.getElementById("cap-curso-form");
    if (!form) return;

    document.getElementById("cap-btn-nuevo-curso")?.addEventListener("click", () => {
      form.reset();
      setFormError("cap-curso-form-error", "");
      togglePanel("cap-curso-form-panel", true);
      document.getElementById("cap-c-codigo")?.focus();
    });

    document.getElementById("cap-curso-cancel")?.addEventListener("click", () => {
      togglePanel("cap-curso-form-panel", false);
      setFormError("cap-curso-form-error", "");
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setFormError("cap-curso-form-error", "");
      const payload = formToObject(form);
      if (payload.horas) payload.horas = Number(payload.horas);
      if (payload.vigencia_meses) payload.vigencia_meses = Number(payload.vigencia_meses);
      try {
        await postJson(`${API}/cursos`, payload);
        togglePanel("cap-curso-form-panel", false);
        form.reset();
        await loadCursos();
      } catch (err) {
        setFormError("cap-curso-form-error", err.message);
      }
    });
  }

  function bindPuestoForm() {
    const form = document.getElementById("cap-puesto-form");
    if (!form) return;

    document.getElementById("cap-btn-nuevo-puesto")?.addEventListener("click", () => {
      form.reset();
      setFormError("cap-puesto-form-error", "");
      togglePanel("cap-puesto-form-panel", true);
      document.getElementById("cap-u-codigo")?.focus();
    });

    document.getElementById("cap-puesto-cancel")?.addEventListener("click", () => {
      togglePanel("cap-puesto-form-panel", false);
      setFormError("cap-puesto-form-error", "");
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      setFormError("cap-puesto-form-error", "");
      try {
        await postJson(`${API}/puestos`, formToObject(form));
        togglePanel("cap-puesto-form-panel", false);
        form.reset();
        await loadPuestos();
        metaPuestos = (await fetchJson(`${API}/puestos`)).puestos || [];
        fillSelect("cap-p-puesto", metaPuestos, "— Sin puesto —");
      } catch (err) {
        setFormError("cap-puesto-form-error", err.message);
      }
    });
  }

  function showView(view) {
    document.querySelectorAll("[data-cap-view]").forEach((el) => {
      const views = (el.dataset.capView || "").split(/\s+/);
      el.classList.toggle("cap-hidden", !views.includes(view));
    });
  }

  async function init() {
    const view = window.CAP_INITIAL_VIEW || "panel";
    showView(view);
    bindCalendar();
    bindPersonaForm();
    bindCursoForm();
    bindPuestoForm();

    if (view === "panel" || view === "programas") {
      try {
        await Promise.all([loadDashboard(), loadEncuentros()]);
      } catch (e) {
        console.error(e);
      }
    }
    if (view === "personas") {
      try {
        await loadMeta();
        await loadPersonas();
      } catch (e) {
        console.error(e);
      }
    }
    if (view === "catalogos") {
      try {
        await Promise.all([loadCursos(), loadPuestos()]);
      } catch (e) {
        console.error(e);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

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

  async function fetchJson(url) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error("Error de red");
    return r.json();
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

  async function loadPersonas() {
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

    selectPersona(items[0].id, list.querySelector(".cap-list-item"));
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

    if (view === "panel" || view === "programas") {
      try {
        await Promise.all([loadDashboard(), loadEncuentros()]);
      } catch (e) {
        console.error(e);
      }
    }
    if (view === "personas") {
      try {
        await loadPersonas();
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

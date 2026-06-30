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

  let personaEditId = null;
  let cursoEditId = null;
  let asistenciaEncuentroId = null;
  let chartPersonal = null;
  let chartCert = null;
  let chartSector = null;
  let chartTipo = null;
  let isoNormaActual = "9001";
  let personaSeleccionadaId = null;
  let certUploadRegistroId = null;
  let taxonomiaCascada = null;
  let taxonomiaListas = null;



  async function fetchJson(url, options) {

    const r = await fetch(url, { credentials: "same-origin", ...options });

    const data = await r.json().catch(() => ({}));

    if (!r.ok) {

      throw new Error(data.error || "Error de red");

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



  async function putJson(url, body) {
    return fetchJson(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }


  async function deleteJson(url) {
    return fetchJson(url, { method: "DELETE" });
  }


  async function uploadFile(url, file) {
    const fd = new FormData();
    fd.append("archivo", file);
    const r = await fetch(url, { method: "POST", credentials: "same-origin", body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || "Error de red");
    return data;
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

    if (panel) panel.classList.toggle("cap-hidden", !show);

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

    const current = sel.value;

    sel.innerHTML = `<option value="">${placeholder}</option>`;

    items.forEach((item) => {

      const opt = document.createElement("option");

      opt.value = item.id;

      opt.textContent = item.codigo ? `${item.codigo} — ${item.nombre}` : item.nombre;

      sel.appendChild(opt);

    });

    if (current) sel.value = current;

  }



  function fillCascadeSelect(selectId, entries, placeholder, disabled) {

    const sel = document.getElementById(selectId);

    if (!sel) return;

    const current = sel.value;

    sel.innerHTML = `<option value="">${placeholder}</option>`;

    entries.forEach(([value, label]) => {

      const opt = document.createElement("option");

      opt.value = value;

      opt.textContent = label;

      sel.appendChild(opt);

    });

    sel.disabled = Boolean(disabled);

    if (current && [...sel.options].some((o) => o.value === current)) {

      sel.value = current;

    }

  }



  async function ensureTaxonomia(force) {

    if (taxonomiaCascada && taxonomiaListas && !force) return taxonomiaCascada;

    const data = await fetchJson(`${API}/cursos/taxonomia`);

    taxonomiaCascada = data.cascada || {};

    taxonomiaListas = data.listas || null;

    return taxonomiaCascada;

  }



  function invalidateTaxonomiaCache() {

    taxonomiaCascada = null;

    taxonomiaListas = null;

  }



  function taxListaEntries(listaKey) {

    const listas = taxonomiaListas || {};

    return (listas[listaKey] || []).map((x) => [x.codigo, x.label || x.nombre || x.codigo]);

  }



  function syncCursoCascada(prefill) {

    const cat = prefill?.categoria ?? document.getElementById("cap-c-categoria")?.value ?? "";

    const tipo = prefill?.tipo ?? document.getElementById("cap-c-tipo")?.value ?? "";

    const origen = prefill?.origen ?? document.getElementById("cap-c-origen")?.value ?? "";

    const modalidad = prefill?.modalidad ?? document.getElementById("cap-c-modalidad")?.value ?? "";



    fillCascadeSelect("cap-c-categoria", taxListaEntries("categorias"), "— Seleccionar —", false);

    fillCascadeSelect("cap-c-tipo", taxListaEntries("tipos"), "— Seleccionar —", false);

    fillCascadeSelect("cap-c-origen", taxListaEntries("origenes"), "— Seleccionar —", false);

    fillCascadeSelect("cap-c-modalidad", taxListaEntries("modalidades"), "— Seleccionar —", false);



    if (cat) document.getElementById("cap-c-categoria").value = cat;

    if (tipo) document.getElementById("cap-c-tipo").value = tipo;

    if (origen) document.getElementById("cap-c-origen").value = origen;

    if (modalidad) document.getElementById("cap-c-modalidad").value = modalidad;

  }



  function bindCursoCascada() {

    document.querySelectorAll(".cap-tax-quick-add").forEach((btn) => {

      btn.addEventListener("click", () => openTaxQuickAdd(btn.dataset.nivel));

    });

  }



  const taxSelected = { categoria: null, tipo: null, origen: null, modalidad: null };

  const taxItemsCache = { categoria: [], tipo: [], origen: [], modalidad: [] };

  const TAX_NIVELES = ["categoria", "tipo", "origen", "modalidad"];

  const TAX_NIVEL_LABELS = {
    categoria: "categoría",
    tipo: "tipo",
    origen: "origen",
    modalidad: "modalidad",
  };



  async function fetchTaxItems(nivel) {

    const params = new URLSearchParams({ nivel });

    return (await fetchJson(`${API}/taxonomia/items?${params}`)).items || [];

  }



  function dedupeTaxItemsByCodigo(items) {

    const seen = new Map();

    items.forEach((item) => {

      if (!seen.has(item.codigo)) seen.set(item.codigo, item);

    });

    return [...seen.values()];

  }



  function renderTaxListError(nivel, message) {

    const ul = document.getElementById(`cap-tax-list-${nivel}`);

    if (ul) ul.innerHTML = `<li class="cap-taxonomia-empty" style="color:#c0392b">${message}</li>`;

  }



  function taxEmptyHint() {

    return "Sin ítems — usá + para agregar";

  }



  function renderTaxList(nivel, items, selectedId) {

    const ul = document.getElementById(`cap-tax-list-${nivel}`);

    if (!ul) return;

    if (!items.length) {

      ul.innerHTML = `<li class="cap-taxonomia-empty">${taxEmptyHint()}</li>`;

      return;

    }

    ul.innerHTML = items

      .map(

        (item) => `<li class="${selectedId === item.id ? "cap-tax-selected" : ""}" data-nivel="${nivel}" data-id="${item.id}" data-codigo="${item.codigo}">

        <span>${item.nombre}</span>

        <span class="cap-tax-actions">

          <button type="button" class="cap-btn cap-btn--xs cap-btn--ghost cap-tax-edit" data-id="${item.id}" data-nombre="${item.nombre.replace(/"/g, "&quot;")}" title="Renombrar"><i class="bi bi-pencil"></i></button>

          <button type="button" class="cap-btn cap-btn--xs cap-btn--ghost cap-tax-del" data-id="${item.id}" title="Eliminar"><i class="bi bi-trash"></i></button>

        </span>

      </li>`

      )

      .join("");



    ul.querySelectorAll("li[data-id]").forEach((li) => {

      li.addEventListener("click", (ev) => {

        if (ev.target.closest(".cap-tax-actions")) return;

        const item = items.find((x) => String(x.id) === li.dataset.id);

        if (item) selectTaxItem(nivel, item);

      });

      li.addEventListener("dblclick", (ev) => {

        if (ev.target.closest(".cap-tax-actions")) return;

        const item = items.find((x) => String(x.id) === li.dataset.id);

        if (item) openTaxFormEdit(nivel, item.id, item.nombre);

      });

    });

    ul.querySelectorAll(".cap-tax-edit").forEach((btn) => {

      btn.addEventListener("click", (ev) => {

        ev.stopPropagation();

        openTaxFormEdit(nivel, parseInt(btn.dataset.id, 10), btn.dataset.nombre);

      });

    });

    ul.querySelectorAll(".cap-tax-del").forEach((btn) => {

      btn.addEventListener("click", async (ev) => {

        ev.stopPropagation();

        if (!confirm("¿Eliminar este ítem?")) return;

        try {

          await deleteJson(`${API}/taxonomia/items/${btn.dataset.id}`);

          await reloadTaxonomia();

        } catch (err) {

          alert(err.message);

        }

      });

    });

  }



  function selectTaxItem(nivel, item) {

    taxSelected[nivel] = item;

    TAX_NIVELES.forEach((n) => {

      const ul = document.getElementById(`cap-tax-list-${n}`);

      if (!ul) return;

      ul.querySelectorAll("li[data-id]").forEach((li) => {

        li.classList.toggle("cap-tax-selected", n === nivel && String(li.dataset.id) === String(item.id));

      });

    });

  }



  async function loadTaxonomiaBrowser() {

    TAX_NIVELES.forEach((nivel) => {

      const ul = document.getElementById(`cap-tax-list-${nivel}`);

      if (ul) ul.innerHTML = '<li class="cap-taxonomia-empty">Cargando...</li>';

    });



    await Promise.all(

      TAX_NIVELES.map(async (nivel) => {

        try {

          taxItemsCache[nivel] = dedupeTaxItemsByCodigo(await fetchTaxItems(nivel));

          renderTaxList(nivel, taxItemsCache[nivel], taxSelected[nivel]?.id);

          setTaxAddButtonState(document.getElementById(`cap-tax-btn-add-${nivel}`));

        } catch (err) {

          renderTaxListError(nivel, err.message);

        }

      })

    );

  }



  async function reloadTaxonomia() {

    invalidateTaxonomiaCache();

    await ensureTaxonomia(true);

    await loadTaxonomiaBrowser();

    syncCursoCascada({

      categoria: document.getElementById("cap-c-categoria")?.value,

      tipo: document.getElementById("cap-c-tipo")?.value,

      origen: document.getElementById("cap-c-origen")?.value,

      modalidad: document.getElementById("cap-c-modalidad")?.value,

    });

  }



  function applyTaxSelectionAfterCreate(createdItem) {

    if (!createdItem?.nivel) return;

    taxSelected[createdItem.nivel] = createdItem;

  }



  function taxContextLabel(nivel) {

    const labels = {

      categoria: "Nueva categoría",

      tipo: "Nuevo tipo",

      origen: "Nuevo origen",

      modalidad: "Nueva modalidad",

    };

    return labels[nivel] || "Nuevo ítem";

  }



  function setTaxAddButtonState(btn) {

    if (!btn) return;

    btn.disabled = false;

    btn.classList.remove("cap-btn--needs-parent");

    btn.setAttribute("aria-disabled", "false");

    const nivel = btn.id?.replace("cap-tax-btn-add-", "") || "";

    btn.title = `Agregar ${TAX_NIVEL_LABELS[nivel] || "ítem"}`;

  }



  function openTaxForm(nivel) {

    document.getElementById("cap-tax-id").value = "";

    document.getElementById("cap-tax-nivel").value = nivel;

    document.getElementById("cap-tax-parent-id").value = "";

    document.getElementById("cap-tax-codigo").value = "";

    document.getElementById("cap-tax-nombre").value = "";

    document.getElementById("cap-tax-codigo-wrap")?.classList.remove("cap-hidden");

    document.getElementById("cap-tax-parent-wrap")?.classList.add("cap-hidden");

    document.getElementById("cap-tax-context").textContent = taxContextLabel(nivel);

    setFormError("cap-tax-form-error", "");

    togglePanel("cap-tax-form-panel", true);

    document.getElementById("cap-tax-form-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });

    document.getElementById("cap-tax-nombre")?.focus();

  }



  function openTaxAdd(nivel) {

    openTaxForm(nivel);

  }



  function openTaxFormEdit(nivel, id, nombre) {

    document.getElementById("cap-tax-id").value = id;

    document.getElementById("cap-tax-nivel").value = nivel;

    document.getElementById("cap-tax-parent-id").value = "";

    document.getElementById("cap-tax-parent-wrap")?.classList.add("cap-hidden");

    document.getElementById("cap-tax-parent-select")?.removeAttribute("name");

    document.getElementById("cap-tax-parent-id")?.setAttribute("name", "parent_id");

    document.getElementById("cap-tax-codigo").value = "";

    document.getElementById("cap-tax-codigo-wrap")?.classList.add("cap-hidden");

    document.getElementById("cap-tax-nombre").value = nombre || "";

    document.getElementById("cap-tax-context").textContent = "Renombrar ítem";

    setFormError("cap-tax-form-error", "");

    togglePanel("cap-tax-form-panel", true);

    document.getElementById("cap-tax-form-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });

    document.getElementById("cap-tax-nombre")?.focus();

  }



  function openTaxQuickAdd(nivel) {

    openTaxAdd(nivel);

  }



  function bindTaxonomiaForm() {

    const form = document.getElementById("cap-tax-form");

    if (!form) return;



    document.getElementById("cap-tax-btn-add-categoria")?.addEventListener("click", () => openTaxAdd("categoria"));

    document.getElementById("cap-tax-btn-add-tipo")?.addEventListener("click", () => openTaxAdd("tipo"));

    document.getElementById("cap-tax-btn-add-origen")?.addEventListener("click", () => openTaxAdd("origen"));

    document.getElementById("cap-tax-btn-add-modalidad")?.addEventListener("click", () => openTaxAdd("modalidad"));



    document.getElementById("cap-tax-cancel")?.addEventListener("click", () => {

      togglePanel("cap-tax-form-panel", false);

      document.getElementById("cap-tax-codigo-wrap")?.classList.remove("cap-hidden");

      document.getElementById("cap-tax-parent-wrap")?.classList.add("cap-hidden");

      document.getElementById("cap-tax-parent-select")?.removeAttribute("name");

      document.getElementById("cap-tax-parent-id")?.setAttribute("name", "parent_id");

      setFormError("cap-tax-form-error", "");

    });



    form.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-tax-form-error", "");

      const id = document.getElementById("cap-tax-id")?.value;

      const nivel = document.getElementById("cap-tax-nivel")?.value;

      const payload = formToObject(form);

      delete payload.parent_id;

      try {

        if (id) {

          await putJson(`${API}/taxonomia/items/${id}`, { nombre: payload.nombre });

          await reloadTaxonomia();

        } else {

          const data = await postJson(`${API}/taxonomia/items`, payload);

          await applyTaxSelectionAfterCreate(data.item);

          await reloadTaxonomia();

        }



        togglePanel("cap-tax-form-panel", false);

        document.getElementById("cap-tax-codigo-wrap")?.classList.remove("cap-hidden");

        document.getElementById("cap-tax-parent-wrap")?.classList.add("cap-hidden");

        document.getElementById("cap-tax-parent-select")?.removeAttribute("name");

        document.getElementById("cap-tax-parent-id")?.setAttribute("name", "parent_id");

        form.reset();

      } catch (err) {

        setFormError("cap-tax-form-error", err.message);

      }

    });

  }



  function cursoClasificacionLabel(c, field) {

    const labels = {

      categoria: c.categoria_label,

      tipo: c.tipo_label,

      origen: c.origen_label,

      modalidad: c.modalidad_label,

    };

    return labels[field] || c[field] || "—";

  }



  function editButton(label, dataset) {

    const attrs = Object.entries(dataset)

      .map(([k, v]) => `data-${k}="${String(v).replace(/"/g, "&quot;")}"`)

      .join(" ");

    return `<button type="button" class="cap-btn cap-btn--sm cap-btn-edit" title="${label}" ${attrs}><i class="bi bi-pencil"></i></button>`;

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

    return encuentros.filter((e) => e.fecha === isoDate(y, m, d));

  }



  function renderCronograma() {

    const labelText = `${MESES[calMonth]} ${calYear}`;

    ["cap-cal-month-label", "cap-cal-month-label-2"].forEach((id) => {

      const label = document.getElementById(id);

      if (label) label.textContent = labelText;

    });



    const grid = document.getElementById("cap-cal-grid");

    const grid2 = document.getElementById("cap-cal-grid-2");

    if (!grid && !grid2) return;



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

            `<span class="cap-cal-event${e.estado === "cancelado" ? " cap-cal-event--cancelado" : ""}" data-encuentro-id="${e.id}" title="${e.titulo}">${e.titulo}</span>`

        )

        .join("");

      html += `<div class="cap-cal-cell${todayCls}"><span class="cap-cal-daynum">${d}</span>${evHtml}</div>`;

    }



    const totalCells = startDow + daysInMonth;

    const trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);

    for (let d = 1; d <= trailing; d++) {

      html += `<div class="cap-cal-cell cap-cal-cell--muted"><span class="cap-cal-daynum">${d}</span></div>`;

    }



    if (grid) grid.innerHTML = html;

    if (grid2) grid2.innerHTML = html;

    document.querySelectorAll("[data-encuentro-id]").forEach((el) => {

      el.addEventListener("click", () => openAsistenciaModal(Number(el.dataset.encuentroId)));

    });

  }



  async function loadEncuentros() {

    const desde = isoDate(calYear, calMonth, 1);

    const hasta = isoDate(calYear, calMonth, lastDayOfMonth(calYear, calMonth));

    const data = await fetchJson(`${API}/encuentros?desde=${desde}&hasta=${hasta}`);

    encuentros = data.encuentros || [];

    renderCronograma();

  }



  async function loadDashboard() {

    const data = await fetchJson(`${API}/dashboard`);

    renderRecursos(data);

    renderKpis(data);

    renderCharts(data);

  }



  function renderKpis(data) {

    const k = data.kpis || {};

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? "—"; };

    set("kpi-personas", k.personas_activas);

    set("kpi-cursos", k.cursos_cargados);

    set("kpi-realizadas", k.realizadas_mes);

    set("kpi-pendientes", k.pendientes);

    set("kpi-vencidas", k.vencidas);

    set("kpi-cumplimiento", `${k.cumplimiento_general || 0}%`);

    set("kpi-horas", k.horas_hombre_mes);

    set("kpi-aprobacion", `${k.tasa_aprobacion || 0}%`);

  }



  function renderCharts(data) {

    const sect = document.getElementById("cap-chart-sectores");

    if (sect) {

      sect.innerHTML = (data.cumplimiento_por_sector || []).map((s) => `

        <div class="cap-bar-row">

          <span class="cap-bar-label">${s.nombre}</span>

          <div class="cap-bar-track"><div class="cap-bar-fill" style="width:${s.pct}%"></div></div>

          <span class="cap-bar-pct">${s.pct}%</span>

        </div>`).join("") || "<p class='cap-empty'>Sin datos</p>";

    }

    const evo = document.getElementById("cap-chart-evolucion");

    if (evo) {

      const items = data.evolucion_mensual || [];

      const max = Math.max(...items.map((i) => i.realizadas), 1);

      evo.innerHTML = `<div class="cap-vbars">${items.map((i) => `

        <div class="cap-bar-row cap-bar-row--vertical">

          <div class="cap-vbar" style="height:${Math.round(i.realizadas / max * 100)}%" title="${i.realizadas}"></div>

          <span class="cap-bar-label">${i.mes.slice(5)}</span>

        </div>`).join("")}</div>`;

    }

    renderDonuts(data);

    renderExtraDonuts(data);

    const tiposEl = document.getElementById("cap-chart-tipos");
    if (tiposEl) {
      tiposEl.innerHTML = (data.cumplimiento_por_tipo || []).map((t) => `
        <div class="cap-bar-row">
          <span class="cap-bar-label">${t.nombre}</span>
          <div class="cap-bar-track"><div class="cap-bar-fill" style="width:${t.pct}%"></div></div>
          <span class="cap-bar-pct">${t.ok}/${t.total} (${t.pct}%)</span>
        </div>`).join("") || "<p class='cap-empty'>Sin datos</p>";
    }

  }



  function renderDonuts(data) {

    if (typeof Chart === "undefined") return;

    const personal = (data.recursos || []).find((r) => r.clave === "personal");

    const cert = (data.recursos || []).find((r) => r.clave === "certificaciones");

    const canvasP = document.getElementById("cap-donut-personal");

    if (canvasP && personal) {

      if (chartPersonal) chartPersonal.destroy();

      chartPersonal = new Chart(canvasP, {

        type: "doughnut",

        data: {

          labels: ["Al día", "Pendiente", "Sin datos"],

          datasets: [{ data: [personal.verde, personal.rojo, personal.gris], backgroundColor: ["#76B947", "#e74c3c", "#94a3b8"] }],

        },

        options: { plugins: { title: { display: true, text: "Personal" } }, maintainAspectRatio: false },

      });

    }

    const canvasC = document.getElementById("cap-donut-cert");

    if (canvasC && cert) {

      if (chartCert) chartCert.destroy();

      chartCert = new Chart(canvasC, {

        type: "doughnut",

        data: {

          labels: ["Vigentes", "Vencidas", "Otros"],

          datasets: [{ data: [cert.verde, cert.rojo, cert.gris], backgroundColor: ["#76B947", "#e74c3c", "#94a3b8"] }],

        },

        options: { plugins: { title: { display: true, text: "Certificaciones" } }, maintainAspectRatio: false },

      });

    }

  }



  function renderExtraDonuts(data) {

    if (typeof Chart === "undefined") return;

    const sectores = data.cumplimiento_por_sector || [];

    const canvasS = document.getElementById("cap-donut-sector");

    if (canvasS && sectores.length) {

      if (chartSector) chartSector.destroy();

      chartSector = new Chart(canvasS, {

        type: "doughnut",

        data: {

          labels: sectores.map((s) => s.nombre),

          datasets: [{ data: sectores.map((s) => s.pct), backgroundColor: ["#76B947", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"] }],

        },

        options: { plugins: { legend: { position: "bottom" } }, maintainAspectRatio: false },

      });

    }

    const tipos = data.cumplimiento_por_tipo || [];

    const canvasT = document.getElementById("cap-donut-tipo");

    if (canvasT && tipos.length) {

      if (chartTipo) chartTipo.destroy();

      chartTipo = new Chart(canvasT, {

        type: "doughnut",

        data: {

          labels: tipos.map((t) => t.nombre),

          datasets: [{ data: tipos.map((t) => t.pct), backgroundColor: ["#76B947", "#3b82f6", "#f59e0b", "#8b5cf6", "#64748b", "#e74c3c"] }],

        },

        options: { plugins: { legend: { position: "bottom" } }, maintainAspectRatio: false },

      });

    }

  }



  async function loadMatriz() {

    const sector = document.getElementById("cap-matriz-sector")?.value || "";

    const estado = document.getElementById("cap-matriz-estado")?.value || "";

    let url = `${API}/matriz?`;

    if (sector) url += `sector_id=${sector}&`;

    if (estado) url += `estado=${estado}&`;

    const data = await fetchJson(url);

    const head = document.getElementById("cap-matriz-head");

    const body = document.getElementById("cap-matriz-body");

    if (!head || !body) return;

    head.innerHTML = `<tr><th class="cap-matriz-sticky">Persona</th>${(data.columnas || []).map((c) => `<th title="${c.nombre}">${c.codigo}</th>`).join("")}</tr>`;

    body.innerHTML = (data.filas || []).map((f) => `

      <tr>

        <td class="cap-matriz-sticky">${f.nombre}</td>

        ${(data.columnas || []).map((c) => {

          const cel = f.celdas[String(c.id)] || { estado: "no_aplica", color: "gris" };

          return `<td class="cap-celda cap-celda--${cel.color}" title="${cel.estado}">${cel.estado === "no_aplica" ? "" : cel.estado.slice(0, 3)}</td>`;

        }).join("")}

      </tr>`).join("") || `<tr><td colspan="${(data.columnas || []).length + 1}" class="cap-empty">Sin datos</td></tr>`;

    const exp = document.getElementById("cap-matriz-export");

    if (exp) exp.href = `${API}/matriz/exportar.xlsx${sector ? `?sector_id=${sector}` : ""}`;

  }



  async function loadAlertas() {

    const tbody = document.getElementById("cap-alertas-body");

    if (!tbody) return;

    const data = await fetchJson(`${API}/alertas`);

    const nivelClass = { critico: "cap-badge--red", advertencia: "cap-badge--yellow", info: "cap-badge--blue" };

    tbody.innerHTML = (data.alertas || []).map((a) => `

      <tr data-alerta-id="${a.id}" class="${a.leida ? "cap-row-leida" : ""}">

        <td><span class="cap-badge ${nivelClass[a.nivel] || ""}">${a.nivel}</span></td>

        <td>${a.titulo}</td>

        <td>${a.mensaje || ""}</td>

        <td>${a.fecha_referencia || ""}</td>

      </tr>`).join("") || `<tr><td colspan="4" class="cap-empty">Sin alertas</td></tr>`;

    tbody.querySelectorAll("tr[data-alerta-id]").forEach((row) => {

      row.addEventListener("click", async () => {

        const id = row.dataset.alertaId;

        if (!id || row.classList.contains("cap-row-leida")) return;

        try {

          await postJson(`${API}/alertas/${id}/leida`, {});

          row.classList.add("cap-row-leida");

        } catch (e) { console.error(e); }

      });

    });

  }



  async function loadProgramas() {

    const el = document.getElementById("cap-programas-list");

    if (!el) return;

    const data = await fetchJson(`${API}/programas`);

    el.innerHTML = (data.programas || []).map((p) => `

      <div class="cap-programa-card">

        <strong>${p.codigo}</strong> — ${p.nombre}

        <span class="cap-badge cap-badge--blue">${p.estado}</span>

        <div class="cap-muted">${p.fecha_inicio || ""} → ${p.fecha_fin || ""}</div>

      </div>`).join("") || "<p class='cap-empty'>No hay programas</p>";

  }



  function bindMatriz() {

    document.getElementById("cap-matriz-sector")?.addEventListener("change", () => loadMatriz().catch(console.error));

    document.getElementById("cap-matriz-estado")?.addEventListener("change", () => loadMatriz().catch(console.error));

  }



  function bindAlertas() {

    document.getElementById("cap-btn-generar-alertas")?.addEventListener("click", async () => {

      const msg = document.getElementById("cap-alertas-notif-msg");

      if (msg) msg.textContent = "";

      const data = await postJson(`${API}/alertas/generar`, {});

      if (msg && data.notificacion) {

        if (data.notificacion.enviado) {

          msg.textContent = `Email enviado a ${(data.notificacion.destinatarios || []).join(", ")}`;

        } else if (data.notificacion.motivo) {

          msg.textContent = `Sin email: ${data.notificacion.motivo}`;

        }

      }

      await loadAlertas();

    });

    document.getElementById("cap-btn-enviar-notif")?.addEventListener("click", async () => {

      const msg = document.getElementById("cap-alertas-notif-msg");

      if (msg) msg.textContent = "Enviando…";

      try {

        const data = await postJson(`${API}/alertas/notificar`, {});

        const n = data.notificacion || {};

        if (msg) {

          msg.textContent = n.enviado

            ? `Email enviado a ${(n.destinatarios || []).join(", ")} (${n.alertas_incluidas || 0} alertas)`

            : `No se envió: ${n.motivo || "error"}`;

        }

      } catch (e) {

        if (msg) msg.textContent = e.message;

      }

    });

  }



  async function loadConfig() {

    const data = await fetchJson(`${API}/configuracion`);

    const cfg = data.config || {};

    const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ""; };

    const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };

    setVal("cap-cfg-dias-vencer", cfg.dias_proximo_vencer ?? 30);

    setVal("cap-cfg-dias-encuentro", cfg.dias_encuentro_proximo ?? 7);

    setVal("cap-cfg-pct-cumplimiento", cfg.pct_cumplimiento_minimo ?? 80);

    setChk("cap-cfg-notif-activo", cfg.notif_email_activo);

    setChk("cap-cfg-notif-vencimiento", cfg.notif_vencimiento !== false);

    setChk("cap-cfg-notif-obligatorio", cfg.notif_obligatorio !== false);

    setChk("cap-cfg-notif-curso", cfg.notif_curso_proximo !== false);

    const emails = document.getElementById("cap-cfg-emails");

    if (emails) emails.value = (cfg.emails_destinatarios || []).join("\n");

    const es = document.getElementById("cap-cfg-emails-sector");

    if (es) es.value = cfg.emails_por_sector && Object.keys(cfg.emails_por_sector).length

      ? JSON.stringify(cfg.emails_por_sector, null, 2) : "";

    const er = document.getElementById("cap-cfg-emails-rol");

    if (er) er.value = cfg.emails_por_rol && Object.keys(cfg.emails_por_rol).length

      ? JSON.stringify(cfg.emails_por_rol, null, 2) : "";

    const ult = document.getElementById("cap-config-ultimo-envio");

    if (ult) ult.textContent = cfg.ultimo_envio_notif ? `Último envío: ${cfg.ultimo_envio_notif}` : "";

  }



  function bindConfig() {

    document.getElementById("cap-config-form")?.addEventListener("submit", async (ev) => {

      ev.preventDefault();

      const err = document.getElementById("cap-config-error");

      if (err) err.textContent = "";

      const parseJsonField = (id) => {

        const raw = document.getElementById(id)?.value?.trim();

        if (!raw) return {};

        return JSON.parse(raw);

      };

      try {

        const payload = {

          dias_proximo_vencer: parseInt(document.getElementById("cap-cfg-dias-vencer")?.value || "30", 10),

          dias_encuentro_proximo: parseInt(document.getElementById("cap-cfg-dias-encuentro")?.value || "7", 10),

          pct_cumplimiento_minimo: parseInt(document.getElementById("cap-cfg-pct-cumplimiento")?.value || "80", 10),

          notif_email_activo: document.getElementById("cap-cfg-notif-activo")?.checked || false,

          notif_vencimiento: document.getElementById("cap-cfg-notif-vencimiento")?.checked !== false,

          notif_obligatorio: document.getElementById("cap-cfg-notif-obligatorio")?.checked !== false,

          notif_curso_proximo: document.getElementById("cap-cfg-notif-curso")?.checked !== false,

          emails_destinatarios: (document.getElementById("cap-cfg-emails")?.value || "")

            .split(/[\n,;]+/).map((e) => e.trim()).filter(Boolean),

          emails_por_sector: parseJsonField("cap-cfg-emails-sector"),

          emails_por_rol: parseJsonField("cap-cfg-emails-rol"),

        };

        await putJson(`${API}/configuracion`, payload);

        if (err) err.textContent = "Configuración guardada.";

        await loadConfig();

      } catch (e) {

        if (err) err.textContent = e.message;

      }

    });

  }



  function bindPersonasFilters() {

    let timer = null;

    const reload = () => loadPersonas(personaSeleccionadaId).catch(console.error);

    document.getElementById("cap-personas-q")?.addEventListener("input", () => {

      clearTimeout(timer);

      timer = setTimeout(reload, 300);

    });

    document.getElementById("cap-personas-sector")?.addEventListener("change", reload);

  }



  function bindGlobalSearch() {

    const input = document.getElementById("cap-global-search");

    const results = document.getElementById("cap-global-search-results");

    if (!input || !results) return;

    let timer = null;

    const hide = () => results.classList.add("cap-hidden");

    const show = () => results.classList.remove("cap-hidden");

    input.addEventListener("input", () => {

      clearTimeout(timer);

      const q = input.value.trim();

      if (q.length < 2) { hide(); return; }

      timer = setTimeout(async () => {

        try {

          const data = await fetchJson(`${API}/busqueda?q=${encodeURIComponent(q)}`);

          const items = data.resultados || [];

          if (!items.length) {

            results.innerHTML = '<div class="cap-empty cap-px">Sin resultados</div>';

          } else {

            results.innerHTML = items.map((r) => `

              <button type="button" class="cap-global-search-item" data-vista="${r.vista}" data-tipo="${r.tipo}" data-id="${r.id}">

                ${r.titulo}<small>${r.subtitulo || r.tipo}</small>

              </button>`).join("");

            results.querySelectorAll(".cap-global-search-item").forEach((btn) => {

              btn.addEventListener("click", () => {

                const vista = btn.dataset.vista;

                const parentUrl = window.location.pathname.replace(/\/app\/?$/, `/${vista === "panel" ? "" : vista}`);

                if (window.parent && window.parent !== window) {

                  window.parent.location.href = parentUrl || "/gos/capacitacion/";

                } else {

                  window.location.href = `/gos/capacitacion/app/?view=${vista}`;

                }

                hide();

                input.value = "";

              });

            });

          }

          show();

        } catch (e) { console.error(e); }

      }, 250);

    });

    document.addEventListener("click", (ev) => {

      if (!document.getElementById("cap-global-search-wrap")?.contains(ev.target)) hide();

    });

  }



  async function loadReporteIso(norma) {

    isoNormaActual = norma;

    const body = document.getElementById("cap-iso-body");

    const resumen = document.getElementById("cap-iso-resumen");

    const pdfLink = document.getElementById("cap-iso-pdf");

    if (!body) return;

    body.innerHTML = '<tr><td colspan="5" class="cap-loading">Cargando...</td></tr>';

    const data = await fetchJson(`${API}/reportes/iso/${norma}`);

    if (pdfLink) pdfLink.href = `${API}/reportes/iso/${norma}.pdf`;

    const r = data.resumen || {};

    if (resumen) {

      resumen.innerHTML = `<div class="cap-iso-kpis">

        <span><strong>${data.titulo}</strong></span>

        <span>Cumplimiento: <strong>${r.cumplimiento_pct || 0}%</strong></span>

        <span>Personas: ${r.personas_evaluadas || 0}</span>

        <span>Requisitos: ${r.requisitos_total || 0} (✓ ${r.cumplidos || 0} · pend. ${r.pendientes || 0} · venc. ${r.vencidos || 0})</span>

      </div>`;

    }

    const estadoBadge = { cumplido: "green", pendiente: "red", vencido: "red", proximo_vencer: "yellow" };

    body.innerHTML = (data.personas || []).map((p) => {

      const det = (p.requisitos || []).map((req) =>

        `<span class="cap-badge cap-badge--${estadoBadge[req.estado] || "gray"}">${req.codigo}: ${req.estado}</span>`

      ).join(" ");

      return `<tr>

        <td>${p.nombre}</td><td>${p.legajo || "—"}</td><td>${p.sector || "—"}</td>

        <td>${p.cumplimiento_pct}%</td><td>${det || "—"}</td></tr>`;

    }).join("") || '<tr><td colspan="5" class="cap-empty">Sin personas con requisitos para esta norma</td></tr>';

  }



  function bindReportes() {

    document.getElementById("cap-reporte-general-pdf")?.setAttribute("href", `${API}/reportes/general.pdf`);

    document.querySelectorAll("#cap-iso-tabs .cap-tab").forEach((tab) => {

      tab.addEventListener("click", async () => {

        document.querySelectorAll("#cap-iso-tabs .cap-tab").forEach((t) => t.classList.remove("active"));

        tab.classList.add("active");

        await loadReporteIso(tab.dataset.norma);

      });

    });

  }



  function bindCertUpload() {

    document.getElementById("cap-cert-upload-file")?.addEventListener("change", async (ev) => {

      const file = ev.target.files?.[0];

      ev.target.value = "";

      if (!file || !certUploadRegistroId) return;

      try {

        const fd = new FormData();

        fd.append("archivo", file);

        await uploadFile(`${API}/registros/${certUploadRegistroId}/certificado`, file);

        if (personaSeleccionadaId) await selectPersona(personaSeleccionadaId);

      } catch (e) {

        alert(e.message);

      }

    });

  }



  function bindSyncVacaciones() {

    document.getElementById("cap-btn-sync-vacaciones")?.addEventListener("click", async () => {

      if (!confirm("¿Importar legajos desde el módulo Vacaciones?")) return;

      try {

        const r = await postJson(`${API}/participantes/sincronizar-vacaciones`, {});

        alert(`Sync: ${r.creados} creados, ${r.actualizados} actualizados, ${r.omitidos} omitidos`);

        await loadPersonas();

      } catch (e) {

        alert(e.message);

      }

    });

  }



  function bindEncuentroForm() {

    document.getElementById("cap-btn-nuevo-encuentro")?.addEventListener("click", () => togglePanel("cap-encuentro-form-panel", true));

    document.getElementById("cap-encuentro-cancel")?.addEventListener("click", () => togglePanel("cap-encuentro-form-panel", false));

    document.getElementById("cap-encuentro-form")?.addEventListener("submit", async (e) => {

      e.preventDefault();

      try {

        await postJson(`${API}/encuentros`, formToObject(e.target));

        togglePanel("cap-encuentro-form-panel", false);

        e.target.reset();

        await loadEncuentros();

      } catch (err) {

        setFormError("cap-encuentro-form-error", err.message);

      }

    });

  }



  function bindCalendar() {

    document.getElementById("cap-cal-prev")?.addEventListener("click", () => {

      calMonth -= 1;

      if (calMonth < 0) { calMonth = 11; calYear -= 1; }

      loadEncuentros();

    });

    document.getElementById("cap-cal-next")?.addEventListener("click", () => {

      calMonth += 1;

      if (calMonth > 11) { calMonth = 0; calYear += 1; }

      loadEncuentros();

    });

    document.getElementById("cap-cal-prev-2")?.addEventListener("click", () => {

      calMonth -= 1;

      if (calMonth < 0) { calMonth = 11; calYear -= 1; }

      loadEncuentros();

    });

    document.getElementById("cap-cal-next-2")?.addEventListener("click", () => {

      calMonth += 1;

      if (calMonth > 11) { calMonth = 0; calYear += 1; }

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



  function openPersonaForm(item) {

    const form = document.getElementById("cap-persona-form");

    if (!form) return;

    personaEditId = item?.id || null;

    form.reset();

    document.getElementById("cap-p-id").value = personaEditId || "";

    if (item) {

      document.getElementById("cap-p-nombre").value = item.nombre || "";

      document.getElementById("cap-p-legajo").value = item.legajo || "";

      document.getElementById("cap-p-email").value = item.email || "";

      if (item.sector_id) document.getElementById("cap-p-sector").value = item.sector_id;

      if (item.puesto_id) document.getElementById("cap-p-puesto").value = item.puesto_id;

    }

    document.getElementById("cap-persona-baja")?.classList.toggle("cap-hidden", !personaEditId);

    setFormError("cap-persona-form-error", "");

    togglePanel("cap-sector-quick", false);

    togglePanel("cap-puesto-quick", false);

    togglePanel("cap-persona-form-panel", true);

    document.getElementById("cap-p-nombre")?.focus();

  }



  function getPersonaInitials(nombre) {
    const parts = String(nombre || "").trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return "?";
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }


  function renderPersonaAvatar(p, size) {
    if (p.tiene_foto) {
      const ts = Date.now();
      return `<img src="${API}/participantes/${p.id}/foto?t=${ts}" alt="">`;
    }
    return getPersonaInitials(p.nombre);
  }


  async function loadPersonas(selectId) {

    const row = document.getElementById("cap-personas-row");

    const detail = document.getElementById("cap-persona-detail");

    const legajoPanel = document.getElementById("cap-legajo-panel");

    if (!row) return;



    row.innerHTML = '<p class="cap-empty">Cargando...</p>';

    const q = document.getElementById("cap-personas-q")?.value?.trim() || "";

    const sectorId = document.getElementById("cap-personas-sector")?.value || "";

    let url = `${API}/participantes?`;

    if (q) url += `q=${encodeURIComponent(q)}&`;

    if (sectorId) url += `sector_id=${sectorId}&`;

    const items = (await fetchJson(url)).participantes || [];



    if (!items.length) {

      row.innerHTML = '<p class="cap-empty">Sin participantes cargados</p>';

      if (detail) detail.innerHTML = '<p class="cap-empty">Agregá personas para ver el legajo.</p>';

      legajoPanel?.classList.add("cap-hidden");

      personaSeleccionadaId = null;

      return;

    }



    row.innerHTML = items

      .map(

        (p) =>

          `<button type="button" class="cap-persona-card" data-id="${p.id}">

            <span class="cap-persona-card__avatar">${renderPersonaAvatar(p)}</span>

            <span class="cap-persona-card__nombre">${p.nombre}</span>

            <span class="cap-persona-card__legajo">${p.legajo || "—"}</span>

          </button>`

      )

      .join("");



    row.querySelectorAll(".cap-persona-card").forEach((btn) => {

      btn.addEventListener("click", () => {

        const id = btn.dataset.id;

        const legajoPanel = document.getElementById("cap-legajo-panel");

        if (personaSeleccionadaId === id && legajoPanel && !legajoPanel.classList.contains("cap-hidden")) {

          deselectPersona();

          return;

        }

        selectPersona(id, btn);

      });

    });



    if (selectId) {

      const targetBtn = row.querySelector(`.cap-persona-card[data-id="${selectId}"]`);

      if (targetBtn) {

        selectPersona(selectId, targetBtn);

        return;

      }

    }

    if (personaSeleccionadaId) {

      const activeBtn = row.querySelector(`.cap-persona-card[data-id="${personaSeleccionadaId}"]`);

      if (activeBtn) {

        activeBtn.classList.add("active");

        return;

      }

    }

    deselectPersona();

  }



  function deselectPersona() {

    document.querySelectorAll(".cap-persona-card").forEach((b) => b.classList.remove("active"));

    personaSeleccionadaId = null;

    const legajoPanel = document.getElementById("cap-legajo-panel");

    const detail = document.getElementById("cap-persona-detail");

    legajoPanel?.classList.add("cap-hidden");

    if (detail) detail.innerHTML = '<p class="cap-empty">Seleccioná una persona para ver su legajo</p>';

  }



  async function selectPersona(id, btn) {

    document.querySelectorAll(".cap-persona-card").forEach((b) => b.classList.remove("active"));

    if (btn) btn.classList.add("active");

    personaSeleccionadaId = id;

    const detail = document.getElementById("cap-persona-detail");

    const legajoPanel = document.getElementById("cap-legajo-panel");

    if (!detail) return;

    legajoPanel?.classList.remove("cap-hidden");

    detail.innerHTML = '<p class="cap-loading">Cargando legajo...</p>';



    const data = await fetchJson(`${API}/participantes/${id}/analitico`);

    const p = data.participante;

    const fotoTs = Date.now();

    const fotoHtml = p.tiene_foto

      ? `<img class="cap-legajo-foto__img" id="cap-legajo-foto-img" src="${API}/participantes/${id}/foto?t=${fotoTs}" alt="Foto de ${p.nombre}">`

      : `<div class="cap-legajo-foto__placeholder" id="cap-legajo-foto-placeholder"><i class="bi bi-person-fill"></i></div>`;



    detail.innerHTML = `

      <div class="cap-legajo-header">

        <div class="cap-legajo-foto">

          ${fotoHtml}

          <div class="cap-legajo-foto__actions">

            <button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" id="cap-btn-subir-foto" title="Subir foto">

              <i class="bi bi-camera"></i>

            </button>

            ${p.tiene_foto ? `<button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" id="cap-btn-quitar-foto" title="Quitar foto"><i class="bi bi-trash"></i></button>` : ""}

          </div>

        </div>

        <div class="cap-legajo-info">

          <h2>${p.nombre}</h2>

          <div class="cap-legajo-meta">

            <div><strong>Legajo:</strong> ${p.legajo || "—"}</div>

            <div>${p.sector_nombre || "—"} · ${p.puesto_nombre || "—"}</div>

          </div>

        </div>

        <div class="cap-toolbar-actions" style="margin-left:auto">

          <a class="cap-btn cap-btn--ghost" href="${API}/participantes/${id}/reporte.pdf" target="_blank"><i class="bi bi-file-earmark-pdf"></i> PDF</a>

          <button type="button" class="cap-btn cap-btn--primary" id="cap-btn-editar-persona">

            <i class="bi bi-pencil"></i> Editar

          </button>

        </div>

      </div>

      <div class="cap-analitico-section">

        <h3>Cursos realizados</h3>

        ${renderCursosConCert(data.cursos_realizados || [])}

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

          (data.planificacion || []).map((pl) => [pl.curso_nombre, pl.fecha_planificada || "—", pl.estado])

        )}

      </div>

    `;



    document.getElementById("cap-btn-editar-persona")?.addEventListener("click", async () => {

      await loadMeta();

      openPersonaForm({

        id: p.id,

        nombre: p.nombre,

        legajo: p.legajo,

        email: null,

        sector_id: p.sector_id,

        puesto_id: p.puesto_id,

      });

    });

    document.getElementById("cap-btn-subir-foto")?.addEventListener("click", () => {

      document.getElementById("cap-foto-upload-file")?.click();

    });

    document.getElementById("cap-btn-quitar-foto")?.addEventListener("click", async () => {

      if (!confirm("¿Quitar la foto del legajo?")) return;

      try {

        await deleteJson(`${API}/participantes/${id}/foto`);

        await selectPersona(id, btn);

        await loadPersonas(id);

      } catch (e) {

        alert(e.message);

      }

    });

    detail.querySelectorAll("[data-cert-registro]").forEach((certBtn) => {

      certBtn.addEventListener("click", () => {

        certUploadRegistroId = parseInt(certBtn.dataset.certRegistro, 10);

        document.getElementById("cap-cert-upload-file")?.click();

      });

    });

  }



  function bindFotoUpload() {

    document.getElementById("cap-foto-upload-file")?.addEventListener("change", async (ev) => {

      const file = ev.target.files?.[0];

      ev.target.value = "";

      if (!file || !personaSeleccionadaId) return;

      try {

        await uploadFile(`${API}/participantes/${personaSeleccionadaId}/foto`, file);

        const activeBtn = document.querySelector(`.cap-persona-card[data-id="${personaSeleccionadaId}"]`);

        await selectPersona(personaSeleccionadaId, activeBtn);

        await loadPersonas(personaSeleccionadaId);

      } catch (e) {

        alert(e.message);

      }

    });

  }



  function renderCursosConCert(cursos) {

    if (!cursos.length) return '<p class="cap-empty" style="padding:.5rem">Sin registros</p>';

    return `<table class="cap-mini-table"><thead><tr><th>Curso</th><th>Fecha</th><th>Nota</th><th>Certificado</th></tr></thead><tbody>${

      cursos.map((c) => `<tr>

        <td>${c.curso_nombre}</td>

        <td>${c.fecha_realizacion}</td>

        <td>${c.nota != null ? c.nota : "—"}</td>

        <td>${c.tiene_certificado

          ? `<a href="${API}/registros/${c.registro_id}/certificado" target="_blank" class="cap-link"><i class="bi bi-file-pdf"></i> Ver</a>`

          : `<button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" data-cert-registro="${c.registro_id}"><i class="bi bi-upload"></i> Subir PDF</button>`}

        </td>

      </tr>`).join("")

    }</tbody></table>`;

  }



  function renderTable(headers, rows) {

    if (!rows.length) return '<p class="cap-empty" style="padding:.5rem">Sin registros</p>';

    return `<table class="cap-mini-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;

  }



  async function loadCursos() {

    const tbody = document.getElementById("cap-cursos-body");

    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="cap-loading">Cargando...</td></tr>';

    const items = (await fetchJson(`${API}/cursos`)).cursos || [];

    window.capCursosCache = items;

    fillSelect("cap-req-curso", items.map((c) => ({ id: c.id, codigo: c.codigo, nombre: c.nombre })), "— Seleccionar curso —");

    if (!tbody) return;

    if (!items.length) {

      tbody.innerHTML = '<tr><td colspan="8" class="cap-empty">Sin cursos cargados</td></tr>';

      return;

    }

    tbody.innerHTML = items

      .map(

        (c) => `<tr>

        <td><strong>${c.codigo}</strong></td>

        <td>${c.nombre}</td>

        <td>${cursoClasificacionLabel(c, "categoria")}</td>

        <td>${cursoClasificacionLabel(c, "tipo")}</td>

        <td>${cursoClasificacionLabel(c, "origen")}</td>

        <td>${cursoClasificacionLabel(c, "modalidad")}</td>

        <td>${c.horas != null ? c.horas : "—"}</td>

        <td class="cap-col-actions">${editButton("Editar", { id: c.id })}</td>

      </tr>`

      )

      .join("");

    bindCatalogTableEdits("cap-cursos-body", (ds) => openCursoForm(items.find((x) => String(x.id) === String(ds.id))));

  }



  async function openCursoForm(item) {

    const form = document.getElementById("cap-curso-form");

    if (!form) return;

    await ensureTaxonomia();

    form.reset();

    cursoEditId = item?.id || null;

    document.getElementById("cap-c-id").value = item?.id || "";

    document.getElementById("cap-c-codigo").value = item?.codigo || "";

    document.getElementById("cap-c-nombre").value = item?.nombre || "";

    document.getElementById("cap-c-descripcion").value = item?.descripcion || "";

    syncCursoCascada({

      categoria: item?.categoria || "",

      tipo: item?.tipo || "",

      origen: item?.origen || "",

      modalidad: item?.modalidad || "",

    });

    document.getElementById("cap-c-horas").value = item?.horas ?? "";

    document.getElementById("cap-c-vigencia").value = item?.vigencia_meses ?? "";

    document.getElementById("cap-c-puntaje").value = item?.puntaje_minimo ?? "";

    document.getElementById("cap-c-eval").checked = Boolean(item?.requiere_evaluacion);

    document.getElementById("cap-curso-baja")?.classList.toggle("cap-hidden", !cursoEditId);

    setFormError("cap-curso-form-error", "");

    togglePanel("cap-curso-form-panel", true);

  }



  function bindCatalogTableEdits(tbodyId, onEdit) {

    document.getElementById(tbodyId)?.querySelectorAll(".cap-btn-edit").forEach((btn) => {

      btn.addEventListener("click", () => onEdit(btn.dataset));

    });

  }



  async function loadSectores() {

    const tbody = document.getElementById("cap-sectores-body");

    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="3" class="cap-loading">Cargando...</td></tr>';

    const items = (await fetchJson(`${API}/sectores`)).sectores || [];

    if (!items.length) {

      tbody.innerHTML = '<tr><td colspan="3" class="cap-empty">Sin sectores cargados</td></tr>';

      return;

    }

    tbody.innerHTML = items

      .map(

        (s) => `<tr>

        <td><strong>${s.codigo}</strong></td>

        <td>${s.nombre}</td>

        <td class="cap-col-actions">${editButton("Editar sector", { id: s.id, codigo: s.codigo, nombre: s.nombre })}</td>

      </tr>`

      )

      .join("");

    bindCatalogTableEdits("cap-sectores-body", openSectorForm);

  }



  async function loadPuestosOptions() {

    const sel = document.getElementById("cap-req-puesto");

    if (!sel) return;

    const items = (await fetchJson(`${API}/puestos`)).puestos || [];

    metaPuestos = items;

    fillSelect("cap-req-puesto", items, "— Seleccionar puesto —");

  }



  async function loadRequisitos() {

    const puestoId = document.getElementById("cap-req-puesto")?.value;

    const tbody = document.getElementById("cap-requisitos-body");

    if (!tbody) return;

    if (!puestoId) {

      tbody.innerHTML = '<tr><td colspan="3" class="cap-empty">Seleccioná un puesto</td></tr>';

      return;

    }

    const items = (await fetchJson(`${API}/requisitos?puesto_id=${puestoId}`)).requisitos || [];

    if (!items.length) {

      tbody.innerHTML = '<tr><td colspan="3" class="cap-empty">Sin requisitos para este puesto</td></tr>';

      return;

    }

    tbody.innerHTML = items.map((r) => `

      <tr>

        <td>${r.curso_codigo} — ${r.curso_nombre}</td>

        <td>${r.obligatorio ? "Sí" : "No"}</td>

        <td><button type="button" class="cap-btn cap-btn--sm cap-btn--danger" data-req-id="${r.id}"><i class="bi bi-trash"></i></button></td>

      </tr>`).join("");

    tbody.querySelectorAll("[data-req-id]").forEach((btn) => {

      btn.addEventListener("click", async () => {

        if (!confirm("¿Eliminar este requisito?")) return;

        await deleteJson(`${API}/requisitos/${btn.dataset.reqId}`);

        await loadRequisitos();

      });

    });

  }



  async function openAsistenciaModal(encuentroId) {

    asistenciaEncuentroId = encuentroId;

    const modal = document.getElementById("cap-asistencia-modal");

    const tbody = document.getElementById("cap-asistencia-body");

    if (!modal || !tbody) return;

    const data = await fetchJson(`${API}/encuentros/${encuentroId}`);

    document.getElementById("cap-asistencia-titulo").textContent = data.titulo || "Asistencia";

    const participantes = data.participantes || [];

    tbody.innerHTML = participantes.map((p) => `

      <tr data-pid="${p.participante_id}">

        <td>${p.nombre}</td>

        <td>

          <select class="cap-input cap-input--sm cap-asist-sel">

            <option value="presente" ${p.asistencia === "presente" ? "selected" : ""}>Presente</option>

            <option value="ausente" ${p.asistencia === "ausente" ? "selected" : ""}>Ausente</option>

            <option value="justificado" ${p.asistencia === "justificado" ? "selected" : ""}>Justificado</option>

          </select>

        </td>

        <td><input class="cap-input cap-input--sm cap-nota-inp" type="number" min="0" max="10" step="0.1" value="${p.nota ?? ""}"></td>

        <td><input type="checkbox" class="cap-aprob-inp" ${p.aprobado ? "checked" : ""}></td>

      </tr>`).join("") || '<tr><td colspan="4" class="cap-empty">Sin participantes</td></tr>';

    modal.classList.remove("cap-hidden");

  }



  function closeAsistenciaModal() {

    document.getElementById("cap-asistencia-modal")?.classList.add("cap-hidden");

    asistenciaEncuentroId = null;

  }



  function openSectorForm(item) {

    const form = document.getElementById("cap-sector-form");

    if (!form) return;

    form.reset();

    document.getElementById("cap-s-id").value = item?.id || "";

    if (item) {

      document.getElementById("cap-s-codigo").value = item.codigo || "";

      document.getElementById("cap-s-nombre").value = item.nombre || "";

    }

    setFormError("cap-sector-form-error", "");

    togglePanel("cap-sector-form-panel", true);

    document.getElementById("cap-s-codigo")?.focus();

  }



  function bindPersonaForm() {

    const form = document.getElementById("cap-persona-form");

    if (!form) return;



    document.getElementById("cap-btn-nueva-persona")?.addEventListener("click", async () => {

      await loadMeta();

      openPersonaForm(null);

    });



    document.getElementById("cap-persona-cancel")?.addEventListener("click", () => {

      personaEditId = null;

      togglePanel("cap-persona-form-panel", false);

      setFormError("cap-persona-form-error", "");

    });



    document.getElementById("cap-p-sector-add")?.addEventListener("click", () => {

      togglePanel("cap-puesto-quick", false);

      togglePanel("cap-sector-quick", true);

    });

    document.getElementById("cap-p-puesto-add")?.addEventListener("click", () => {

      togglePanel("cap-sector-quick", false);

      togglePanel("cap-puesto-quick", true);

    });

    document.getElementById("cap-sector-quick-cancel")?.addEventListener("click", () => togglePanel("cap-sector-quick", false));

    document.getElementById("cap-puesto-quick-cancel")?.addEventListener("click", () => togglePanel("cap-puesto-quick", false));



    document.getElementById("cap-sector-quick-save")?.addEventListener("click", async () => {

      const codigo = document.getElementById("cap-sector-quick-codigo")?.value.trim();

      const nombre = document.getElementById("cap-sector-quick-nombre")?.value.trim();

      if (!codigo || !nombre) {

        setFormError("cap-persona-form-error", "Código y nombre del sector son obligatorios.");

        return;

      }

      try {

        const data = await postJson(`${API}/sectores`, { codigo, nombre });

        await loadMeta();

        document.getElementById("cap-p-sector").value = data.sector.id;

        togglePanel("cap-sector-quick", false);

        setFormError("cap-persona-form-error", "");

      } catch (err) {

        setFormError("cap-persona-form-error", err.message);

      }

    });



    document.getElementById("cap-puesto-quick-save")?.addEventListener("click", async () => {

      const codigo = document.getElementById("cap-puesto-quick-codigo")?.value.trim();

      const nombre = document.getElementById("cap-puesto-quick-nombre")?.value.trim();

      if (!codigo || !nombre) {

        setFormError("cap-persona-form-error", "Código y nombre del puesto son obligatorios.");

        return;

      }

      try {

        const data = await postJson(`${API}/puestos`, { codigo, nombre });

        await loadMeta();

        document.getElementById("cap-p-puesto").value = data.puesto.id;

        togglePanel("cap-puesto-quick", false);

        setFormError("cap-persona-form-error", "");

      } catch (err) {

        setFormError("cap-persona-form-error", err.message);

      }

    });



    form.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-persona-form-error", "");

      const payload = formToObject(form);

      if (!payload.legajo) {

        setFormError("cap-persona-form-error", "El legajo es obligatorio.");

        return;

      }

      delete payload.id;

      if (payload.sector_id) payload.sector_id = Number(payload.sector_id);

      if (payload.puesto_id) payload.puesto_id = Number(payload.puesto_id);

      try {

        let data;

        if (personaEditId) {

          data = await putJson(`${API}/participantes/${personaEditId}`, payload);

        } else {

          data = await postJson(`${API}/participantes`, payload);

        }

        personaEditId = null;

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



    document.getElementById("cap-btn-nuevo-curso")?.addEventListener("click", () => openCursoForm(null));

    document.getElementById("cap-btn-importar-cursos")?.addEventListener("click", () => {

      document.getElementById("cap-import-cursos-file")?.click();

    });

    document.getElementById("cap-import-cursos-file")?.addEventListener("change", async (e) => {

      const file = e.target.files?.[0];

      if (!file) return;

      try {

        const r = await uploadFile(`${API}/cursos/importar`, file);

        alert(`Importación: ${r.creados} creados, ${r.actualizados} actualizados.${r.errores?.length ? "\nErrores:\n" + r.errores.join("\n") : ""}`);

        await loadCursos();

      } catch (err) {

        alert(err.message);

      }

      e.target.value = "";

    });



    document.getElementById("cap-curso-cancel")?.addEventListener("click", () => {

      cursoEditId = null;

      togglePanel("cap-curso-form-panel", false);

      setFormError("cap-curso-form-error", "");

    });



    document.getElementById("cap-curso-baja")?.addEventListener("click", async () => {

      if (!cursoEditId || !confirm("¿Dar de baja este curso?")) return;

      try {

        await deleteJson(`${API}/cursos/${cursoEditId}`);

        togglePanel("cap-curso-form-panel", false);

        cursoEditId = null;

        await loadCursos();

      } catch (err) {

        setFormError("cap-curso-form-error", err.message);

      }

    });



    form.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-curso-form-error", "");

      const payload = formToObject(form);

      payload.requiere_evaluacion = document.getElementById("cap-c-eval")?.checked || false;

      if (payload.horas) payload.horas = Number(payload.horas);

      if (payload.vigencia_meses) payload.vigencia_meses = Number(payload.vigencia_meses);

      if (payload.puntaje_minimo) payload.puntaje_minimo = Number(payload.puntaje_minimo);

      delete payload.id;

      try {

        if (cursoEditId) {

          await putJson(`${API}/cursos/${cursoEditId}`, payload);

        } else {

          await postJson(`${API}/cursos`, payload);

        }

        togglePanel("cap-curso-form-panel", false);

        form.reset();

        cursoEditId = null;

        await loadCursos();

      } catch (err) {

        setFormError("cap-curso-form-error", err.message);

      }

    });

  }



  function bindRequisitos() {

    document.getElementById("cap-req-puesto")?.addEventListener("change", () => loadRequisitos().catch(console.error));

    document.getElementById("cap-btn-agregar-requisito")?.addEventListener("click", async () => {

      const puestoId = document.getElementById("cap-req-puesto")?.value;

      const cursoId = document.getElementById("cap-req-curso")?.value;

      setFormError("cap-requisito-error", "");

      if (!puestoId || !cursoId) {

        setFormError("cap-requisito-error", "Seleccioná puesto y curso");

        return;

      }

      try {

        await postJson(`${API}/requisitos`, { puesto_id: Number(puestoId), curso_id: Number(cursoId), obligatorio: true });

        await loadRequisitos();

      } catch (err) {

        setFormError("cap-requisito-error", err.message);

      }

    });

  }



  function bindAsistenciaModal() {

    ["cap-asistencia-cerrar", "cap-asistencia-cancel", "cap-asistencia-backdrop"].forEach((id) => {

      document.getElementById(id)?.addEventListener("click", closeAsistenciaModal);

    });

    document.getElementById("cap-asistencia-guardar")?.addEventListener("click", async () => {

      if (!asistenciaEncuentroId) return;

      const rows = document.querySelectorAll("#cap-asistencia-body tr[data-pid]");

      const asistencias = Array.from(rows).map((tr) => ({

        participante_id: Number(tr.dataset.pid),

        asistencia: tr.querySelector(".cap-asist-sel")?.value || "presente",

        nota: tr.querySelector(".cap-nota-inp")?.value || null,

        aprobado: tr.querySelector(".cap-aprob-inp")?.checked || false,

      }));

      try {

        await postJson(`${API}/encuentros/${asistenciaEncuentroId}/asistencias`, { asistencias });

        closeAsistenciaModal();

        await loadEncuentros();

      } catch (err) {

        alert(err.message);

      }

    });

  }



  function bindImportPersonas() {

    document.getElementById("cap-btn-importar-personas")?.addEventListener("click", () => {

      document.getElementById("cap-import-personas-file")?.click();

    });

    document.getElementById("cap-import-personas-file")?.addEventListener("change", async (e) => {

      const file = e.target.files?.[0];

      if (!file) return;

      try {

        const r = await uploadFile(`${API}/participantes/importar`, file);

        alert(`Importación: ${r.creados} creados, ${r.actualizados} actualizados.${r.errores?.length ? "\nErrores:\n" + r.errores.join("\n") : ""}`);

        await loadPersonas();

      } catch (err) {

        alert(err.message);

      }

      e.target.value = "";

    });

    document.getElementById("cap-persona-baja")?.addEventListener("click", async () => {

      if (!personaEditId || !confirm("¿Dar de baja esta persona?")) return;

      try {

        await deleteJson(`${API}/participantes/${personaEditId}`);

        personaEditId = null;

        togglePanel("cap-persona-form-panel", false);

        await loadPersonas();

      } catch (err) {

        setFormError("cap-persona-form-error", err.message);

      }

    });

  }



  function bindSectorForm() {

    const form = document.getElementById("cap-sector-form");

    if (!form) return;



    document.getElementById("cap-btn-nuevo-sector")?.addEventListener("click", () => openSectorForm(null));

    document.getElementById("cap-sector-cancel")?.addEventListener("click", () => {

      togglePanel("cap-sector-form-panel", false);

      setFormError("cap-sector-form-error", "");

    });



    form.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-sector-form-error", "");

      const payload = formToObject(form);

      const id = document.getElementById("cap-s-id")?.value;

      delete payload.id;

      try {

        if (id) {

          await putJson(`${API}/sectores/${id}`, payload);

        } else {

          await postJson(`${API}/sectores`, payload);

        }

        togglePanel("cap-sector-form-panel", false);

        form.reset();

        await loadSectores();

        metaSectores = (await fetchJson(`${API}/sectores`)).sectores || [];

        fillSelect("cap-p-sector", metaSectores, "— Sin sector —");

      } catch (err) {

        setFormError("cap-sector-form-error", err.message);

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
    bindCursoCascada();
    bindTaxonomiaForm();
    await ensureTaxonomia();

    bindSectorForm();

    bindMatriz();

    bindAlertas();

    bindConfig();

    bindGlobalSearch();

    bindPersonasFilters();

    bindReportes();

    bindCertUpload();

    bindFotoUpload();

    bindSyncVacaciones();

    bindEncuentroForm();

    bindRequisitos();

    bindAsistenciaModal();

    bindImportPersonas();



    if (view === "panel") {

      try { await Promise.all([loadDashboard(), loadEncuentros()]); } catch (e) { console.error(e); }

    }

    if (view === "cronograma") {

      try { await loadEncuentros(); } catch (e) { console.error(e); }

    }

    if (view === "programas") {

      try { await loadProgramas(); } catch (e) { console.error(e); }

      try { await loadPuestosOptions(); } catch (e) { console.error(e); }

      try { await loadCursos(); } catch (e) { console.error(e); }

    }

    if (view === "matriz") {

      try {

        await loadMeta();

        fillSelect("cap-matriz-sector", metaSectores, "Todos los sectores");

        await loadMatriz();

      } catch (e) { console.error(e); }

    }

    if (view === "alertas") {

      try { await loadAlertas(); } catch (e) { console.error(e); }

    }

    if (view === "configuracion") {

      try { await loadConfig(); } catch (e) { console.error(e); }

    }

    if (view === "reportes") {

      try { await loadReporteIso(isoNormaActual); } catch (e) { console.error(e); }

    }

    if (view === "personas") {

      try {

        await loadMeta();

        fillSelect("cap-personas-sector", metaSectores, "Todos los sectores");

        await loadPersonas();

      } catch (e) { console.error(e); }

    }

    if (view === "catalogos") {

      try { await loadCursos(); } catch (e) { console.error(e); }

      try { await loadSectores(); } catch (e) { console.error(e); }

      try {

        await loadTaxonomiaBrowser();

      } catch (e) {

        console.error("Taxonomía:", e);

      }

      if (taxonomiaCascada) syncCursoCascada();

    }

  }



  if (document.readyState === "loading") {

    document.addEventListener("DOMContentLoaded", init);

  } else {

    init();

  }

})();



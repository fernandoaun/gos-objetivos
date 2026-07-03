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
  let currentCapView = "panel";
  let encuentroEditId = null;
  let encAccionEncuentroId = null;

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
  let matrizParticipanteId = window.CAP_INITIAL_PARTICIPANTE_ID || null;
  let matrizParticipanteNombre = null;
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



  function navigateToCapView(vista, params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== "") {
        query.set(key, String(value));
      }
    });
    const qs = query.toString();
    const parentPath = vista === "panel" ? "/gos/capacitacion/" : `/gos/capacitacion/${vista}`;
    const parentUrl = qs ? `${parentPath}?${qs}` : parentPath;

    if (window.parent && window.parent !== window) {
      window.parent.location.href = parentUrl;
      return;
    }

    const appQuery = new URLSearchParams({ view: vista, ...params });
    window.location.href = `/gos/capacitacion/app/?${appQuery}`;
  }



  function updateMatrizPersonaFilter() {
    const wrap = document.getElementById("cap-matriz-persona-filter");
    const nombre = document.getElementById("cap-matriz-persona-nombre");
    if (!wrap || !nombre) return;

    if (matrizParticipanteId) {
      nombre.textContent = matrizParticipanteNombre || `Persona #${matrizParticipanteId}`;
      wrap.classList.remove("cap-hidden");
      return;
    }

    nombre.textContent = "";
    wrap.classList.add("cap-hidden");
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



  function normPuestoId(id) {

    const n = Number(id);

    return Number.isFinite(n) ? n : null;

  }



  function encPuestoSetHas(puestoId) {

    const id = normPuestoId(puestoId);

    return id !== null && encPuestosSeleccionados.has(id);

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

            `<span class="cap-cal-event${e.estado === "cancelado" ? " cap-cal-event--cancelado" : ""}" data-encuentro-id="${e.id}" title="${e.titulo}${currentCapView === "cronograma" ? " — Clic para modificar o eliminar" : ""}">${e.titulo}</span>`

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

      el.addEventListener("click", (ev) => {

        ev.stopPropagation();

        onCalEventClick(Number(el.dataset.encuentroId));

      });

    });

  }



  function onCalEventClick(encuentroId) {

    if (currentCapView === "cronograma") {

      openEncAccionModal(encuentroId).catch(console.error);

      return;

    }

    openAsistenciaModal(encuentroId).catch(console.error);

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



  function renderMatrizTable(data, head, body, { showPersonaColumn = true } = {}) {

    if (!head || !body) return;

    const columnas = data.columnas || [];

    const filas = data.filas || [];

    const personaTh = showPersonaColumn ? '<th class="cap-matriz-sticky">Persona</th>' : "";

    head.innerHTML = `<tr>${personaTh}${columnas.map((c) => `<th title="${c.nombre}">${c.codigo}</th>`).join("")}</tr>`;

    const colSpan = columnas.length + (showPersonaColumn ? 1 : 0);

    body.innerHTML = filas.map((f) => `

      <tr>

        ${showPersonaColumn ? `<td class="cap-matriz-sticky">${f.nombre}</td>` : ""}

        ${columnas.map((c) => {

          const cel = f.celdas[String(c.id)] || { estado: "no_aplica", color: "gris" };

          return `<td class="cap-celda cap-celda--${cel.color}" title="${cel.estado}">${cel.estado === "no_aplica" ? "" : cel.estado.slice(0, 3)}</td>`;

        }).join("")}

      </tr>`).join("") || `<tr><td colspan="${colSpan}" class="cap-empty">Sin datos</td></tr>`;

  }



  async function loadLegajoMatriz(participanteId) {

    const head = document.getElementById("cap-legajo-matriz-head");

    const body = document.getElementById("cap-legajo-matriz-body");

    if (!head || !body) return;

    body.innerHTML = '<tr><td class="cap-loading">Cargando...</td></tr>';

    const data = await fetchJson(`${API}/matriz?participante_id=${participanteId}`);

    renderMatrizTable(data, head, body, { showPersonaColumn: false });

  }



  async function loadMatriz() {

    const sector = document.getElementById("cap-matriz-sector")?.value || "";

    const estado = document.getElementById("cap-matriz-estado")?.value || "";

    let url = `${API}/matriz?`;

    if (sector) url += `sector_id=${sector}&`;

    if (estado) url += `estado=${estado}&`;

    if (matrizParticipanteId) url += `participante_id=${matrizParticipanteId}&`;

    const data = await fetchJson(url);

    const head = document.getElementById("cap-matriz-head");

    const body = document.getElementById("cap-matriz-body");

    if (!head || !body) return;

    if (matrizParticipanteId && !matrizParticipanteNombre) {
      const fila = (data.filas || []).find((f) => f.participante_id === matrizParticipanteId);
      if (fila?.nombre) {
        matrizParticipanteNombre = fila.nombre;
        updateMatrizPersonaFilter();
      }
    }

    renderMatrizTable(data, head, body);

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



  let programaCursosIds = [];
  let programaSeleccionadoId = null;
  let programasCache = [];

  function refreshProgramaCursoSelect() {

    const all = window.capCursosCache || [];

    const available = all.filter((c) => !programaCursosIds.includes(c.id));

    fillSelect(

      "cap-req-curso",

      available.map((c) => ({ id: c.id, codigo: c.codigo, nombre: c.nombre })),

      available.length ? "— Seleccionar curso —" : "— Todos los cursos ya están en el programa —"

    );

  }



  function bindMatriz() {

    document.getElementById("cap-matriz-sector")?.addEventListener("change", () => loadMatriz().catch(console.error));

    document.getElementById("cap-matriz-estado")?.addEventListener("change", () => loadMatriz().catch(console.error));

    document.getElementById("cap-matriz-persona-clear")?.addEventListener("click", () => {
      matrizParticipanteId = null;
      matrizParticipanteNombre = null;
      updateMatrizPersonaFilter();
      loadMatriz().catch(console.error);
    });

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



  let encPuestosSeleccionados = new Set();
  let encPersonasCache = [];



  function getEncPuestosSeleccionados() {

    return Array.from(encPuestosSeleccionados).filter((id) => normPuestoId(id) !== null);

  }



  function renderEncPuestos() {

    const el = document.getElementById("cap-enc-puestos");

    if (!el) return;

    const items = metaPuestos || [];

    if (!items.length) {

      el.innerHTML = `

        <p class="cap-empty">No hay puestos cargados</p>

        <button type="button" class="cap-btn cap-btn--sm cap-btn--ghost" id="cap-enc-puesto-add">Agregar puesto</button>`;

      document.getElementById("cap-enc-puesto-add")?.addEventListener("click", () => {

        togglePanel("cap-enc-instructor-quick", false);

        togglePanel("cap-enc-empresa-quick", false);

        togglePanel("cap-enc-puesto-quick", true);

        document.getElementById("cap-enc-puesto-quick-codigo")?.focus();

      });

      return;

    }

    el.innerHTML = `

      ${items.map((p) => `

      <label class="cap-check-item">

        <input type="checkbox" value="${p.id}" data-enc-puesto ${encPuestoSetHas(p.id) ? "checked" : ""}>

        <span>${p.codigo} — ${p.nombre}</span>

      </label>`).join("")}

      <button type="button" class="cap-btn cap-btn--sm cap-btn--ghost cap-check-grid__action" id="cap-enc-puesto-add">+ Agregar puesto</button>`;

    el.querySelectorAll("[data-enc-puesto]").forEach((cb) => {

      cb.addEventListener("change", () => {

        const id = normPuestoId(cb.value);

        if (id === null) return;

        if (cb.checked) encPuestosSeleccionados.add(id);

        else encPuestosSeleccionados.delete(id);

        onEncPuestosChange().catch(console.error);

      });

    });

    document.getElementById("cap-enc-puesto-add")?.addEventListener("click", () => {

      togglePanel("cap-enc-instructor-quick", false);

      togglePanel("cap-enc-empresa-quick", false);

      togglePanel("cap-enc-puesto-quick", true);

      document.getElementById("cap-enc-puesto-quick-codigo")?.focus();

    });

  }



  async function onEncPuestosChange() {

    await loadEncPersonas();

    await loadEncCursos();

  }



  async function loadEncPersonas(selectedIds = null, { todas = false } = {}) {

    const el = document.getElementById("cap-enc-personas");

    const countEl = document.getElementById("cap-enc-personas-count");

    if (!el) return;

    const puestoIds = getEncPuestosSeleccionados();

    if (!todas && !puestoIds.length) {

      encPersonasCache = [];

      el.innerHTML = '<p class="cap-empty">Seleccioná al menos un puesto</p>';

      if (countEl) countEl.textContent = "";

      return;

    }

    el.innerHTML = '<p class="cap-loading">Cargando personas...</p>';

    const url = todas

      ? `${API}/participantes?`

      : `${API}/participantes?puesto_ids=${puestoIds.join(",")}`;

    const data = await fetchJson(url);

    encPersonasCache = data.participantes || [];

    if (!encPersonasCache.length) {

      if (!todas && puestoIds.length) {

        const totalData = await fetchJson(`${API}/participantes?`);

        const total = (totalData.participantes || []).length;

        const nombresPuesto = puestoIds

          .map((id) => metaPuestos.find((p) => normPuestoId(p.id) === id))

          .filter(Boolean)

          .map((p) => `${p.codigo} — ${p.nombre}`)

          .join(", ");

        el.innerHTML = `

          <p class="cap-empty">No hay personas con el puesto ${nombresPuesto || "seleccionado"} asignado.</p>

          <p class="cap-form-hint">En <strong>Personas</strong>, editá cada legajo y elegí el puesto correspondiente.</p>

          ${total ? `<button type="button" class="cap-btn cap-btn--sm cap-btn--ghost" id="cap-enc-cargar-todas">Mostrar las ${total} personas activas</button>` : ""}`;

        document.getElementById("cap-enc-cargar-todas")?.addEventListener("click", () => {

          loadEncPersonas(null, { todas: true }).catch(console.error);

        });

      } else {

        el.innerHTML = '<p class="cap-empty">No hay personas en los puestos seleccionados</p>';

      }

      if (countEl) countEl.textContent = "0 personas";

      return;

    }

    const selected = selectedIds instanceof Set ? selectedIds : null;

    const avisoTodas = todas

      ? '<p class="cap-form-hint cap-mb">Mostrando todas las personas activas. Asigná el puesto en Personas para filtrar automáticamente.</p>'

      : "";

    el.innerHTML = `${avisoTodas}${encPersonasCache.map((p) => `

      <label class="cap-check-item">

        <input type="checkbox" value="${p.id}" data-enc-persona ${selected ? (selected.has(p.id) || selected.has(normPuestoId(p.id)) ? "checked" : "") : "checked"}>

        <span>${p.nombre}${p.legajo ? ` <span class="cap-muted">(${p.legajo})</span>` : ""}${p.puesto_nombre ? "" : ' <span class="cap-muted">(sin puesto)</span>'}</span>

      </label>`).join("")}`;

    updateEncPersonasCount();

    el.querySelectorAll("[data-enc-persona]").forEach((cb) => {

      cb.addEventListener("change", updateEncPersonasCount);

    });

  }



  function updateEncPersonasCount() {

    const countEl = document.getElementById("cap-enc-personas-count");

    if (!countEl) return;

    const total = document.querySelectorAll("[data-enc-persona]").length;

    const sel = document.querySelectorAll("[data-enc-persona]:checked").length;

    countEl.textContent = total ? `${sel} de ${total} seleccionadas` : "";

  }



  function getEncPersonasSeleccionadas() {

    return Array.from(document.querySelectorAll("[data-enc-persona]:checked")).map((cb) => Number(cb.value));

  }



  async function loadEncCursos() {

    const sel = document.getElementById("cap-enc-curso");

    if (!sel) return;

    const current = sel.value;

    const puestoIds = getEncPuestosSeleccionados();

    let cursos = window.capCursosCache || [];

    if (puestoIds.length) {

      const data = await fetchJson(`${API}/requisitos?puesto_ids=${puestoIds.join(",")}`);

      const ids = new Set((data.requisitos || []).map((r) => r.curso_id).filter(Boolean));

      const filtrados = cursos.filter((c) => ids.has(c.id));

      if (filtrados.length) cursos = filtrados;

    }

    fillSelect("cap-enc-curso", cursos.map((c) => ({ id: c.id, codigo: c.codigo, nombre: c.nombre })), "— Seleccionar curso —");

    if (current) sel.value = current;

    onEncCursoChange();

  }



  function onEncCursoChange() {

    const cursoId = document.getElementById("cap-enc-curso")?.value;

    const origenSel = document.getElementById("cap-enc-origen");

    if (!cursoId || !origenSel) return;

    const curso = (window.capCursosCache || []).find((c) => String(c.id) === String(cursoId));

    if (curso?.origen && !origenSel.value) origenSel.value = curso.origen;

    toggleEncEmpresaCapacitadora();

    updateEncHoraFin();

  }



  function toggleEncEmpresaCapacitadora() {

    const origen = document.getElementById("cap-enc-origen")?.value;

    const wrap = document.getElementById("cap-enc-empresa-wrap");

    const sel = document.getElementById("cap-enc-empresa");

    if (!wrap || !sel) return;

    const esExterna = origen === "externa";

    wrap.classList.toggle("cap-hidden", !esExterna);

    sel.required = esExterna;

    if (!esExterna) sel.value = "";

  }



  async function loadEncCatalogos() {

    await ensureTaxonomia();

    fillCascadeSelect("cap-enc-origen", taxListaEntries("origenes"), "— Seleccionar origen —", false);

    const [instData, empData] = await Promise.all([

      fetchJson(`${API}/instructores`),

      fetchJson(`${API}/empresas-capacitadoras`),

    ]);

    fillSelect(

      "cap-enc-instructor",

      (instData.instructores || []).map((i) => ({ id: i.id, nombre: i.nombre })),

      "— Seleccionar capacitador —"

    );

    fillSelect(

      "cap-enc-empresa",

      (empData.empresas_capacitadoras || []).map((e) => ({ id: e.id, nombre: e.nombre })),

      "— Seleccionar empresa —"

    );

  }



  function updateEncuentroFormMode(editing) {

    const hint = document.getElementById("cap-encuentro-form-hint");

    const submit = document.getElementById("cap-encuentro-submit");

    const delBtn = document.getElementById("cap-encuentro-eliminar");

    if (hint) {

      hint.textContent = editing

        ? "Modificá los datos de la programación."

        : "Programá una capacitación eligiendo puestos, personas, curso y fecha.";

    }

    if (submit) submit.textContent = editing ? "Guardar cambios" : "Programar capacitación";

    if (delBtn) delBtn.classList.toggle("cap-hidden", !editing);

  }



  function setEncFormVal(id, val) {

    const el = document.getElementById(id);

    if (el) el.value = val ?? "";

  }



  function formatTimeInput(value) {

    if (!value) return "";

    return String(value).slice(0, 5);

  }



  function calcEncHoraFin(horaInicio, horasDuracion) {

    if (!horaInicio || horasDuracion == null || horasDuracion === "") return "";

    const parts = String(horaInicio).slice(0, 5).split(":");

    if (parts.length < 2) return "";

    const h = Number(parts[0]);

    const m = Number(parts[1]);

    if (Number.isNaN(h) || Number.isNaN(m)) return "";

    const totalMinutes = h * 60 + m + Math.round(Number(horasDuracion) * 60);

    const dayMinutes = totalMinutes % (24 * 60);

    const nh = Math.floor(dayMinutes / 60);

    const nm = dayMinutes % 60;

    return `${String(nh).padStart(2, "0")}:${String(nm).padStart(2, "0")}`;

  }



  function updateEncHoraFin() {

    const cursoId = document.getElementById("cap-enc-curso")?.value;

    const horaInicio = document.getElementById("cap-enc-hora-inicio")?.value;

    const horaFinEl = document.getElementById("cap-enc-hora-fin");

    if (!horaFinEl) return;

    if (!cursoId || !horaInicio) {

      horaFinEl.value = "";

      return;

    }

    const curso = (window.capCursosCache || []).find((c) => String(c.id) === String(cursoId));

    horaFinEl.value = calcEncHoraFin(horaInicio, curso?.horas);

  }



  function appendEncSelectOption(selectId, item) {

    const sel = document.getElementById(selectId);

    if (!sel || !item?.id) return;

    const opt = document.createElement("option");

    opt.value = item.id;

    opt.textContent = item.codigo ? `${item.codigo} — ${item.nombre}` : item.nombre;

    sel.appendChild(opt);

    sel.value = String(item.id);

  }



  function closeEncQuickForms() {

    togglePanel("cap-enc-empresa-quick", false);

    togglePanel("cap-enc-instructor-quick", false);

    togglePanel("cap-enc-puesto-quick", false);

  }



  async function resetEncuentroForm() {

    const form = document.getElementById("cap-encuentro-form");

    if (form) form.reset();

    encuentroEditId = null;

    encPuestosSeleccionados = new Set();

    setFormError("cap-encuentro-form-error", "");

    closeEncQuickForms();

    updateEncuentroFormMode(false);

    renderEncPuestos();

    await loadEncPersonas();

    await loadEncCursos();

    toggleEncEmpresaCapacitadora();

  }



  async function openEncuentroForm() {

    if (!metaPuestos.length) {

      try { await loadPuestosOptions(); } catch (e) { console.error(e); }

    }

    if (!window.capCursosCache?.length) {

      try { await loadCursos(); } catch (e) { console.error(e); }

    }

    try { await loadEncCatalogos(); } catch (e) { console.error(e); }

    await resetEncuentroForm();

    togglePanel("cap-encuentro-form-panel", true);

  }



  async function openEncuentroFormEdit(encuentroId) {

    closeEncAccionModal();

    if (!metaPuestos.length) {

      try { await loadPuestosOptions(); } catch (e) { console.error(e); }

    }

    if (!window.capCursosCache?.length) {

      try { await loadCursos(); } catch (e) { console.error(e); }

    }

    try { await loadEncCatalogos(); } catch (e) { console.error(e); }

    const form = document.getElementById("cap-encuentro-form");

    if (form) form.reset();

    setFormError("cap-encuentro-form-error", "");

    encuentroEditId = encuentroId;

    updateEncuentroFormMode(true);

    const data = await fetchJson(`${API}/encuentros/${encuentroId}`);

    const participantes = data.participantes || [];

    const participanteIds = new Set(participantes.map((p) => p.participante_id));

    encPuestosSeleccionados = new Set(

      participantes.map((p) => normPuestoId(p.puesto_id)).filter((id) => id !== null)

    );

    if (!encPuestosSeleccionados.size && metaPuestos.length) {

      encPuestosSeleccionados = new Set(metaPuestos.map((p) => normPuestoId(p.id)).filter((id) => id !== null));

    }

    renderEncPuestos();

    await loadEncPersonas(participanteIds);

    await loadEncCursos();

    const cursoSel = document.getElementById("cap-enc-curso");

    if (cursoSel && data.curso_id) {

      const cursoId = String(data.curso_id);

      if (!Array.from(cursoSel.options).some((o) => o.value === cursoId)) {

        const curso = (window.capCursosCache || []).find((c) => String(c.id) === cursoId);

        if (curso) {

          const opt = document.createElement("option");

          opt.value = curso.id;

          opt.textContent = `${curso.codigo} — ${curso.nombre}`;

          cursoSel.appendChild(opt);

        }

      }

      cursoSel.value = cursoId;

    }

    setEncFormVal("cap-enc-fecha", data.fecha);

    setEncFormVal("cap-enc-hora-inicio", formatTimeInput(data.hora_inicio));

    setEncFormVal("cap-enc-hora-fin", formatTimeInput(data.hora_fin));

    setEncFormVal("cap-enc-origen", data.origen || "");

    setEncFormVal("cap-enc-empresa", data.empresa_capacitadora_id || "");

    setEncFormVal("cap-enc-instructor", data.instructor_id || "");

    setEncFormVal("cap-enc-lugar", data.lugar || "");

    setEncFormVal("cap-enc-link", data.link_virtual || "");

    toggleEncEmpresaCapacitadora();

    updateEncHoraFin();

    togglePanel("cap-encuentro-form-panel", true);

  }



  async function eliminarEncuentro(encuentroId) {

    if (!confirm("¿Eliminar esta programación? Esta acción no se puede deshacer.")) return;

    await deleteJson(`${API}/encuentros/${encuentroId}`);

    closeEncAccionModal();

    togglePanel("cap-encuentro-form-panel", false);

    encuentroEditId = null;

    updateEncuentroFormMode(false);

    await loadEncuentros();

  }



  async function openEncAccionModal(encuentroId) {

    encAccionEncuentroId = encuentroId;

    const modal = document.getElementById("cap-enc-accion-modal");

    if (!modal) return;

    let ev = encuentros.find((e) => e.id === encuentroId);

    if (!ev) {

      try {

        ev = await fetchJson(`${API}/encuentros/${encuentroId}`);

      } catch (e) {

        console.error(e);

        return;

      }

    }

    const tituloEl = document.getElementById("cap-enc-accion-titulo");

    const fechaEl = document.getElementById("cap-enc-accion-fecha");

    if (tituloEl) tituloEl.textContent = ev.titulo || "Programación";

    if (fechaEl) {

      const parts = (ev.fecha || "").split("-");

      const fechaTxt = parts.length === 3

        ? `${parts[2]}/${parts[1]}/${parts[0]}`

        : (ev.fecha || "");

      const hora = ev.hora_inicio ? ` · ${formatTimeInput(ev.hora_inicio)}` : "";

      fechaEl.textContent = `${fechaTxt}${hora}`;

    }

    modal.classList.remove("cap-hidden");

  }



  function closeEncAccionModal() {

    document.getElementById("cap-enc-accion-modal")?.classList.add("cap-hidden");

    encAccionEncuentroId = null;

  }



  function bindEncAccionModal() {

    document.getElementById("cap-enc-accion-backdrop")?.addEventListener("click", closeEncAccionModal);

    document.getElementById("cap-enc-accion-cerrar")?.addEventListener("click", closeEncAccionModal);

    document.getElementById("cap-enc-accion-editar")?.addEventListener("click", () => {

      if (!encAccionEncuentroId) return;

      openEncuentroFormEdit(encAccionEncuentroId).catch(console.error);

    });

    document.getElementById("cap-enc-accion-asistencia")?.addEventListener("click", () => {

      if (!encAccionEncuentroId) return;

      const id = encAccionEncuentroId;

      closeEncAccionModal();

      openAsistenciaModal(id).catch(console.error);

    });

    document.getElementById("cap-enc-accion-eliminar")?.addEventListener("click", () => {

      if (!encAccionEncuentroId) return;

      eliminarEncuentro(encAccionEncuentroId).catch((err) => alert(err.message));

    });

  }



  function bindEncuentroForm() {

    document.getElementById("cap-btn-nuevo-encuentro")?.addEventListener("click", () => openEncuentroForm().catch(console.error));

    document.getElementById("cap-encuentro-cancel")?.addEventListener("click", () => {

      closeEncQuickForms();

      togglePanel("cap-encuentro-form-panel", false);

      encuentroEditId = null;

      updateEncuentroFormMode(false);

    });

    document.getElementById("cap-encuentro-eliminar")?.addEventListener("click", () => {

      if (!encuentroEditId) return;

      eliminarEncuentro(encuentroEditId).catch((err) => setFormError("cap-encuentro-form-error", err.message));

    });

    document.getElementById("cap-enc-sel-todos")?.addEventListener("click", () => {

      document.querySelectorAll("[data-enc-persona]").forEach((cb) => { cb.checked = true; });

      updateEncPersonasCount();

    });

    document.getElementById("cap-enc-sel-ninguno")?.addEventListener("click", () => {

      document.querySelectorAll("[data-enc-persona]").forEach((cb) => { cb.checked = false; });

      updateEncPersonasCount();

    });

    document.getElementById("cap-enc-curso")?.addEventListener("change", onEncCursoChange);

    document.getElementById("cap-enc-hora-inicio")?.addEventListener("change", updateEncHoraFin);

    document.getElementById("cap-enc-hora-inicio")?.addEventListener("input", updateEncHoraFin);

    document.getElementById("cap-enc-origen")?.addEventListener("change", toggleEncEmpresaCapacitadora);

    document.getElementById("cap-enc-empresa-add")?.addEventListener("click", () => {

      togglePanel("cap-enc-instructor-quick", false);

      togglePanel("cap-enc-puesto-quick", false);

      togglePanel("cap-enc-empresa-quick", true);

      document.getElementById("cap-enc-empresa-quick-nombre")?.focus();

    });

    document.getElementById("cap-enc-instructor-add")?.addEventListener("click", () => {

      togglePanel("cap-enc-empresa-quick", false);

      togglePanel("cap-enc-puesto-quick", false);

      togglePanel("cap-enc-instructor-quick", true);

      document.getElementById("cap-enc-instructor-quick-nombre")?.focus();

    });

    document.getElementById("cap-enc-puesto-quick-cancel")?.addEventListener("click", () => togglePanel("cap-enc-puesto-quick", false));

    document.getElementById("cap-enc-puesto-quick-save")?.addEventListener("click", async () => {

      const codigo = document.getElementById("cap-enc-puesto-quick-codigo")?.value.trim();

      const nombre = document.getElementById("cap-enc-puesto-quick-nombre")?.value.trim();

      if (!codigo || !nombre) {

        setFormError("cap-encuentro-form-error", "Código y nombre del puesto son obligatorios.");

        return;

      }

      try {

        const data = await postJson(`${API}/puestos`, { codigo, nombre });

        await loadPuestosOptions();

        const puestoId = normPuestoId(data.puesto?.id);

        if (puestoId !== null) encPuestosSeleccionados.add(puestoId);

        document.getElementById("cap-enc-puesto-quick-codigo").value = "";

        document.getElementById("cap-enc-puesto-quick-nombre").value = "";

        togglePanel("cap-enc-puesto-quick", false);

        setFormError("cap-encuentro-form-error", "");

        renderEncPuestos();

        await onEncPuestosChange();

      } catch (err) {

        setFormError("cap-encuentro-form-error", err.message);

      }

    });

    document.getElementById("cap-enc-empresa-quick-cancel")?.addEventListener("click", () => togglePanel("cap-enc-empresa-quick", false));

    document.getElementById("cap-enc-instructor-quick-cancel")?.addEventListener("click", () => togglePanel("cap-enc-instructor-quick", false));

    document.getElementById("cap-enc-empresa-quick-save")?.addEventListener("click", async () => {

      const nombre = document.getElementById("cap-enc-empresa-quick-nombre")?.value.trim();

      if (!nombre) {

        setFormError("cap-encuentro-form-error", "Indicá el nombre de la empresa capacitadora");

        return;

      }

      try {

        const data = await postJson(`${API}/empresas-capacitadoras`, { nombre });

        appendEncSelectOption("cap-enc-empresa", data.empresa_capacitadora);

        document.getElementById("cap-enc-empresa-quick-nombre").value = "";

        togglePanel("cap-enc-empresa-quick", false);

        setFormError("cap-encuentro-form-error", "");

      } catch (err) {

        setFormError("cap-encuentro-form-error", err.message);

      }

    });

    document.getElementById("cap-enc-instructor-quick-save")?.addEventListener("click", async () => {

      const nombre = document.getElementById("cap-enc-instructor-quick-nombre")?.value.trim();

      if (!nombre) {

        setFormError("cap-encuentro-form-error", "Indicá el nombre del capacitador");

        return;

      }

      try {

        const data = await postJson(`${API}/instructores`, { nombre });

        appendEncSelectOption("cap-enc-instructor", data.instructor);

        document.getElementById("cap-enc-instructor-quick-nombre").value = "";

        togglePanel("cap-enc-instructor-quick", false);

        setFormError("cap-encuentro-form-error", "");

      } catch (err) {

        setFormError("cap-encuentro-form-error", err.message);

      }

    });

    document.getElementById("cap-encuentro-form")?.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-encuentro-form-error", "");

      const participanteIds = getEncPersonasSeleccionadas();

      if (!getEncPuestosSeleccionados().length) {

        setFormError("cap-encuentro-form-error", "Seleccioná al menos un puesto");

        return;

      }

      if (!participanteIds.length) {

        setFormError("cap-encuentro-form-error", "Seleccioná al menos una persona");

        return;

      }

      const body = formToObject(e.target);

      body.participante_ids = participanteIds;

      if (!body.curso_id) {

        setFormError("cap-encuentro-form-error", "Seleccioná un curso");

        return;

      }

      if (!body.fecha) {

        setFormError("cap-encuentro-form-error", "Indicá la fecha");

        return;

      }

      if (body.origen === "externa" && !body.empresa_capacitadora_id) {

        setFormError("cap-encuentro-form-error", "Seleccioná la empresa capacitadora");

        return;

      }

      try {

        if (encuentroEditId) {

          await putJson(`${API}/encuentros/${encuentroEditId}`, body);

        } else {

          await postJson(`${API}/encuentros`, body);

        }

        togglePanel("cap-encuentro-form-panel", false);

        encuentroEditId = null;

        updateEncuentroFormMode(false);

        await resetEncuentroForm();

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



  function formatFecha(iso) {
    if (!iso) return "—";
    const [y, m, d] = iso.split("-");
    if (!y || !m || !d) return iso;
    return `${d}/${m}/${y}`;
  }



  function renderLegajoCampo(label, value) {
    const texto = value || "—";
    return `<div class="cap-legajo-campo"><dt>${label}</dt><dd>${texto}</dd></div>`;
  }



  function renderLegajoPerfil(p) {
    const observaciones = p.observaciones
      ? `<div class="cap-legajo-campo cap-legajo-campo--full"><dt>Observaciones</dt><dd>${p.observaciones}</dd></div>`
      : "";

    return `
      <div class="cap-legajo-datos">
        <h3>Datos de la persona</h3>
        <dl class="cap-legajo-grid">
          ${renderLegajoCampo("Legajo", p.legajo)}
          ${renderLegajoCampo("DNI", p.dni)}
          ${renderLegajoCampo("Email", p.email)}
          ${renderLegajoCampo("Teléfono", p.telefono)}
          ${renderLegajoCampo("Sector", p.sector_nombre)}
          ${renderLegajoCampo("Puesto", p.puesto_nombre)}
          ${renderLegajoCampo("Fecha de ingreso", formatFecha(p.fecha_ingreso))}
          ${observaciones}
        </dl>
      </div>
    `;
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



    const { participante: p } = await fetchJson(`${API}/participantes/${id}`);

    const nombreDisplay = p.nombre_completo || p.nombre;

    const fotoTs = Date.now();

    const fotoHtml = p.tiene_foto

      ? `<img class="cap-legajo-foto__img" id="cap-legajo-foto-img" src="${API}/participantes/${id}/foto?t=${fotoTs}" alt="Foto de ${nombreDisplay}">`

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

          <h2>${nombreDisplay}</h2>

          <div class="cap-legajo-meta">

            <div><strong>Legajo:</strong> ${p.legajo || "—"}</div>

            <div>${p.sector_nombre || "—"} · ${p.puesto_nombre || "—"}</div>

          </div>

        </div>

        <div class="cap-toolbar-actions" style="margin-left:auto">

          <button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" id="cap-btn-ver-matriz" title="Ver matriz de capacitaciones">

            <i class="bi bi-grid-3x3-gap"></i> Matriz

          </button>

          <a class="cap-btn cap-btn--ghost" href="${API}/participantes/${id}/reporte.pdf" target="_blank"><i class="bi bi-file-earmark-pdf"></i> PDF</a>

          <button type="button" class="cap-btn cap-btn--primary" id="cap-btn-editar-persona">

            <i class="bi bi-pencil"></i> Editar

          </button>

        </div>

      </div>

      ${renderLegajoPerfil(p)}

      <div class="cap-legajo-matriz cap-hidden" id="cap-legajo-matriz">

        <h3>Matriz de capacitaciones</h3>

        <div class="cap-matriz-wrap cap-matriz-wrap--legajo">

          <table class="cap-matriz-table" id="cap-legajo-matriz-table">

            <thead id="cap-legajo-matriz-head"><tr><th>Curso</th></tr></thead>

            <tbody id="cap-legajo-matriz-body"><tr><td class="cap-loading">Cargando...</td></tr></tbody>

          </table>

        </div>

        <div class="cap-leyenda cap-leyenda--compact">

          <span class="cap-leyenda-item cap-leyenda--verde">Vigente</span>

          <span class="cap-leyenda-item cap-leyenda--amarillo">Próximo a vencer</span>

          <span class="cap-leyenda-item cap-leyenda--rojo">Vencido</span>

          <span class="cap-leyenda-item cap-leyenda--azul">Programado</span>

          <span class="cap-leyenda-item cap-leyenda--gris">No aplica</span>

        </div>

      </div>

    `;



    document.getElementById("cap-btn-editar-persona")?.addEventListener("click", async () => {

      await loadMeta();

      openPersonaForm({

        id: p.id,

        nombre: nombreDisplay,

        legajo: p.legajo,

        email: p.email,

        sector_id: p.sector_id,

        puesto_id: p.puesto_id,

      });

    });

    document.getElementById("cap-btn-ver-matriz")?.addEventListener("click", async () => {

      const section = document.getElementById("cap-legajo-matriz");

      const btn = document.getElementById("cap-btn-ver-matriz");

      if (!section) return;

      const willShow = section.classList.contains("cap-hidden");

      if (willShow) {

        section.classList.remove("cap-hidden");

        btn?.classList.add("cap-btn--active");

        await loadLegajoMatriz(id);

        section.scrollIntoView({ behavior: "smooth", block: "nearest" });

      } else {

        section.classList.add("cap-hidden");

        btn?.classList.remove("cap-btn--active");

      }

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

    if (document.getElementById("cap-req-curso")) refreshProgramaCursoSelect();

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

    const items = (await fetchJson(`${API}/puestos`)).puestos || [];

    metaPuestos = items;

    fillSelect("cap-req-puesto", items, "— Seleccionar puesto —");

    fillSelect("cap-prog-puesto", items, "— Seleccionar puesto —");

    fillSelect("cap-p-puesto", items, "— Sin puesto —");

    const formOpen = !document.getElementById("cap-encuentro-form-panel")?.classList.contains("cap-hidden");

    if (formOpen) {

      renderEncPuestos();

      if (getEncPuestosSeleccionados().length) {

        await loadEncPersonas();

      }

    }

  }



  function programaEstadoLabel(estado) {

    const labels = {

      borrador: "Borrador",

      programado: "Programado",

      en_curso: "En curso",

      finalizado: "Finalizado",

      cancelado: "Cancelado",

    };

    return labels[estado] || estado || "—";

  }



  async function loadProgramas() {
    const cards = document.getElementById("cap-programas-cards");
    if (!cards) return;
    cards.innerHTML = '<div class="cap-loading">Cargando...</div>';
    const tipo = document.getElementById("cap-prog-filtro-tipo")?.value || "";
    const qs = tipo ? `?tipo=${encodeURIComponent(tipo)}` : "";
    const data = await fetchJson(`${API}/programas${qs}`);
    programasCache = data.programas || [];
    if (!programasCache.length) {
      cards.innerHTML = '<div class="cap-empty">Todavía no hay programas. Creá el primero con <strong>Nuevo programa</strong>.</div>';
      return;
    }
    cards.innerHTML = programasCache.map((p) => {
      const puestos = (p.puestos || []).map((x) => x.nombre).join(", ") || p.puesto_nombre || "Sin puestos";
      const tipoLabel = p.tipo === "externo" ? "Externo" : "Interno";
      return `
      <article class="cap-card ${p.id === programaSeleccionadoId ? "cap-card--active" : ""}" data-programa-id="${p.id}">
        <div class="cap-card-head">
          <strong>${escapeHtml(p.nombre)}</strong>
          <span class="cap-badge">${tipoLabel}</span>
        </div>
        <div class="cap-card-meta">
          <span><i class="bi bi-diagram-3"></i> ${p.planes_count || 0} planes</span>
          <span><i class="bi bi-journal-text"></i> ${p.cursos_count || 0} cursos</span>
          <span><i class="bi bi-person-badge"></i> ${p.puestos_count || 0} puestos</span>
        </div>
        <p class="cap-card-sub">${escapeHtml(puestos)}</p>
        <div class="cap-card-actions">
          <button type="button" class="cap-btn cap-btn--sm cap-btn--primary" data-prog-open="${p.id}">Abrir</button>
        </div>
      </article>`;
    }).join("");
    cards.querySelectorAll("[data-prog-open], article[data-programa-id]").forEach((el) => {
      el.addEventListener("click", (ev) => {
        if (ev.target.closest("button") && !ev.target.closest("[data-prog-open]")) return;
        const id = Number(el.dataset.progOpen || el.dataset.programaId);
        selectPrograma(id).catch(console.error);
      });
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderPuestosChecks(containerId, selectedIds = []) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const selected = new Set((selectedIds || []).map(String));
    if (!metaPuestos.length) {
      el.innerHTML = '<p class="cap-empty">No hay puestos cargados en catálogos.</p>';
      return;
    }
    el.innerHTML = metaPuestos.map((p) => `
      <label class="cap-check">
        <input type="checkbox" value="${p.id}" ${selected.has(String(p.id)) ? "checked" : ""}>
        <span>${escapeHtml(p.nombre)}</span>
      </label>`).join("");
  }

  function selectedPuestoIds(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`))
      .map((inp) => Number(inp.value));
  }

  async function selectPrograma(programaId) {
    programaSeleccionadoId = programaId;
    const detalle = document.getElementById("cap-programa-detalle");
    const titleEl = document.getElementById("cap-programa-detalle-title");
    const planesEl = document.getElementById("cap-programa-planes");
    if (!detalle || !planesEl) return;
    detalle.classList.remove("cap-hidden");
    planesEl.innerHTML = '<div class="cap-loading">Cargando estructura...</div>';
    const data = await fetchJson(`${API}/programas/${programaId}`);
    const programa = data.programa;
    programasCache = programasCache.map((p) => (p.id === programa.id ? { ...p, ...programa } : p));
    if (titleEl) titleEl.textContent = `${programa.nombre} (${programa.tipo === "externo" ? "Externo" : "Interno"})`;
    renderPuestosChecks("cap-programa-puestos-detalle", (programa.puestos || []).map((p) => p.id));
    renderProgramaPlanes(programa);
    await loadProgramas();
    detalle.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderProgramaPlanes(programa) {
    const planesEl = document.getElementById("cap-programa-planes");
    if (!planesEl) return;
    const planes = programa.planes || [];
    if (!planes.length) {
      planesEl.innerHTML = '<p class="cap-empty">Este programa no tiene planes. Agregá el primero.</p>';
      return;
    }
    const allCursos = window.capCursosCache || [];
    planesEl.innerHTML = planes.map((plan) => {
      const usados = new Set((plan.cursos || []).map((c) => c.curso_id));
      const disponibles = allCursos.filter((c) => !usados.has(c.id));
      const cursosHtml = (plan.cursos || []).map((c, i) => {
        const badges = (c.tambien_en || []).map((p) => `<span class="cap-badge cap-badge--soft">También en: ${escapeHtml(p.nombre)}</span>`).join(" ");
        return `<li class="cap-plan-curso">
          <span class="cap-col-num">${i + 1}</span>
          <span>${escapeHtml(c.curso_codigo)} — ${escapeHtml(c.curso_nombre)} ${badges}</span>
          <button type="button" class="cap-btn cap-btn--sm cap-btn--danger" data-del-plan-curso="${c.id}" title="Quitar"><i class="bi bi-trash"></i></button>
        </li>`;
      }).join("") || '<li class="cap-empty">Sin cursos en este plan</li>';
      return `<section class="cap-plan-block" data-plan-id="${plan.id}">
        <div class="cap-plan-head">
          <h4>${escapeHtml(plan.nombre)}</h4>
          <button type="button" class="cap-btn cap-btn--sm cap-btn--danger" data-del-plan="${plan.id}" title="Eliminar plan"><i class="bi bi-trash"></i></button>
        </div>
        <ul class="cap-plan-cursos">${cursosHtml}</ul>
        <div class="cap-input-group">
          <select class="cap-input" data-plan-curso-select="${plan.id}">
            <option value="">— Agregar curso —</option>
            ${disponibles.map((c) => `<option value="${c.id}">${escapeHtml(c.codigo)} — ${escapeHtml(c.nombre)}</option>`).join("")}
          </select>
          <button type="button" class="cap-btn cap-btn--primary" data-add-plan-curso="${plan.id}"><i class="bi bi-plus-lg"></i></button>
        </div>
      </section>`;
    }).join("");

    planesEl.querySelectorAll("[data-add-plan-curso]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const planId = Number(btn.dataset.addPlanCurso);
        const sel = planesEl.querySelector(`[data-plan-curso-select="${planId}"]`);
        const cursoId = Number(sel?.value || 0);
        if (!cursoId) return;
        try {
          await postJson(`${API}/planes/${planId}/cursos`, { curso_id: cursoId });
          await selectPrograma(programaSeleccionadoId);
        } catch (err) {
          alert(err.message);
        }
      });
    });
    planesEl.querySelectorAll("[data-del-plan-curso]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("¿Quitar este curso del plan?")) return;
        try {
          await deleteJson(`${API}/plan-cursos/${btn.dataset.delPlanCurso}`);
          await selectPrograma(programaSeleccionadoId);
        } catch (err) {
          alert(err.message);
        }
      });
    });
    planesEl.querySelectorAll("[data-del-plan]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("¿Eliminar este plan y sus cursos?")) return;
        try {
          await deleteJson(`${API}/planes/${btn.dataset.delPlan}`);
          await selectPrograma(programaSeleccionadoId);
        } catch (err) {
          alert(err.message);
        }
      });
    });
  }

  function openProgramaForm(programa = null) {
    const form = document.getElementById("cap-programa-form");
    if (form) form.reset();
    setFormError("cap-programa-form-error", "");
    document.getElementById("cap-prog-id").value = programa?.id || "";
    document.getElementById("cap-prog-nombre").value = programa?.nombre || "";
    document.getElementById("cap-prog-codigo").value = programa?.codigo || "";
    document.getElementById("cap-prog-descripcion").value = programa?.descripcion || "";
    const tipo = programa?.tipo || "interno";
    form.querySelectorAll('input[name="tipo"]').forEach((inp) => {
      inp.checked = inp.value === tipo;
    });
    renderPuestosChecks("cap-prog-puestos", (programa?.puestos || []).map((p) => p.id));
    document.getElementById("cap-programa-submit").textContent = programa ? "Guardar cambios" : "Crear programa";
    togglePanel("cap-programa-form-panel", true);
    document.getElementById("cap-prog-nombre")?.focus();
  }

  function bindProgramaForm() {
    document.getElementById("cap-btn-nuevo-programa")?.addEventListener("click", async () => {
      if (!metaPuestos.length) {
        try { await loadPuestosOptions(); } catch (e) { console.error(e); }
      }
      if (!(window.capCursosCache || []).length) {
        try {
          const data = await fetchJson(`${API}/cursos`);
          window.capCursosCache = data.cursos || [];
        } catch (e) { console.error(e); }
      }
      openProgramaForm();
    });
    document.getElementById("cap-programa-cancel")?.addEventListener("click", () => {
      togglePanel("cap-programa-form-panel", false);
    });
    document.getElementById("cap-prog-filtro-tipo")?.addEventListener("change", () => {
      loadProgramas().catch(console.error);
    });
    document.getElementById("cap-btn-editar-programa")?.addEventListener("click", async () => {
      if (!programaSeleccionadoId) return;
      const data = await fetchJson(`${API}/programas/${programaSeleccionadoId}`);
      openProgramaForm(data.programa);
    });
    document.getElementById("cap-btn-agregar-plan")?.addEventListener("click", async () => {
      if (!programaSeleccionadoId) return;
      const nombre = prompt("Nombre del plan (ej. Seguridad, Técnico, Liderazgo):");
      if (!nombre || !nombre.trim()) return;
      try {
        await postJson(`${API}/programas/${programaSeleccionadoId}/planes`, { nombre: nombre.trim() });
        await selectPrograma(programaSeleccionadoId);
      } catch (err) {
        alert(err.message);
      }
    });
    document.getElementById("cap-btn-guardar-puestos")?.addEventListener("click", async () => {
      if (!programaSeleccionadoId) return;
      setFormError("cap-programa-puestos-error", "");
      try {
        await putJson(`${API}/programas/${programaSeleccionadoId}`, {
          puesto_ids: selectedPuestoIds("cap-programa-puestos-detalle"),
        });
        await selectPrograma(programaSeleccionadoId);
      } catch (err) {
        setFormError("cap-programa-puestos-error", err.message);
      }
    });
    document.getElementById("cap-programa-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      setFormError("cap-programa-form-error", "");
      const body = formToObject(e.target);
      body.puesto_ids = selectedPuestoIds("cap-prog-puestos");
      body.tipo = e.target.querySelector('input[name="tipo"]:checked')?.value || "interno";
      const id = body.id ? Number(body.id) : null;
      delete body.id;
      try {
        const data = id
          ? await putJson(`${API}/programas/${id}`, body)
          : await postJson(`${API}/programas`, body);
        togglePanel("cap-programa-form-panel", false);
        e.target.reset();
        await loadProgramas();
        if (data.programa?.id) await selectPrograma(data.programa.id);
      } catch (err) {
        setFormError("cap-programa-form-error", err.message);
      }
    });
  }

  async function loadRequisitos() {
    return;
  }

  async function agregarCursoAlPrograma() {
    return;
  }

  function bindRequisitos() {
  }

  let asistenciaCursoMeta = { requiere_evaluacion: false, puntaje_minimo: null };

  function calcEstadoAsistencia(asistio, nota) {
    if (asistio === false) return "No asistió";
    if (asistio !== true) return "Pendiente";
    if (!asistenciaCursoMeta.requiere_evaluacion) return "Aprobó";
    if (nota === null || nota === "" || Number.isNaN(Number(nota))) return "No aprobó";
    const minimo = Number(asistenciaCursoMeta.puntaje_minimo ?? 0);
    return Number(nota) >= minimo ? "Aprobó" : "No aprobó";
  }

  function refreshAsistenciaRow(tr) {
    const asistio = tr.querySelector(".cap-asist-sel")?.value;
    const notaInp = tr.querySelector(".cap-nota-inp");
    const estadoEl = tr.querySelector(".cap-estado-calc");
    const asistioBool = asistio === "presente" ? true : (asistio === "ausente" ? false : null);
    if (notaInp) {
      const showNota = asistenciaCursoMeta.requiere_evaluacion && asistioBool === true;
      notaInp.disabled = !showNota;
      if (!showNota) notaInp.value = "";
    }
    if (estadoEl) estadoEl.textContent = calcEstadoAsistencia(asistioBool, notaInp?.value);
  }

  async function openAsistenciaModal(encuentroId) {
    asistenciaEncuentroId = encuentroId;
    const modal = document.getElementById("cap-asistencia-modal");
    const tbody = document.getElementById("cap-asistencia-body");
    if (!modal || !tbody) return;
    const data = await fetchJson(`${API}/encuentros/${encuentroId}`);
    document.getElementById("cap-asistencia-titulo").textContent = data.titulo || "Cierre de cronograma";
    asistenciaCursoMeta = {
      requiere_evaluacion: !!data.curso_requiere_evaluacion,
      puntaje_minimo: data.curso_puntaje_minimo,
    };
    const participantes = data.participantes || [];
    tbody.innerHTML = participantes.map((p) => {
      const asistio = p.asistio === true ? "presente" : (p.asistio === false ? "ausente" : (p.asistencia || "inscripto"));
      return `
      <tr data-pid="${p.participante_id}">
        <td>${escapeHtml(p.nombre)}</td>
        <td>
          <select class="cap-input cap-input--sm cap-asist-sel">
            <option value="inscripto" ${asistio === "inscripto" ? "selected" : ""}>Pendiente</option>
            <option value="presente" ${asistio === "presente" ? "selected" : ""}>Sí</option>
            <option value="ausente" ${asistio === "ausente" ? "selected" : ""}>No</option>
          </select>
        </td>
        <td><input class="cap-input cap-input--sm cap-nota-inp" type="number" min="0" max="100" step="0.1" value="${p.nota ?? ""}"></td>
        <td><span class="cap-estado-calc">${escapeHtml(p.estado || "Pendiente")}</span></td>
      </tr>`;
    }).join("") || '<tr><td colspan="4" class="cap-empty">Sin participantes</td></tr>';
    tbody.querySelectorAll("tr[data-pid]").forEach((tr) => {
      refreshAsistenciaRow(tr);
      tr.querySelector(".cap-asist-sel")?.addEventListener("change", () => refreshAsistenciaRow(tr));
      tr.querySelector(".cap-nota-inp")?.addEventListener("input", () => refreshAsistenciaRow(tr));
    });
    modal.classList.remove("cap-hidden");
  }

  function closeAsistenciaModal() {
    asistenciaEncuentroId = null;
    document.getElementById("cap-asistencia-modal")?.classList.add("cap-hidden");
  }

  function bindAsistenciaModal() {
    ["cap-asistencia-cerrar", "cap-asistencia-cancel", "cap-asistencia-backdrop"].forEach((id) => {
      document.getElementById(id)?.addEventListener("click", closeAsistenciaModal);
    });
    document.getElementById("cap-asistencia-guardar")?.addEventListener("click", async () => {
      if (!asistenciaEncuentroId) return;
      const rows = document.querySelectorAll("#cap-asistencia-body tr[data-pid]");
      const registros = Array.from(rows).map((tr) => {
        const asistencia = tr.querySelector(".cap-asist-sel")?.value || "inscripto";
        return {
          participante_id: Number(tr.dataset.pid),
          asistencia,
          asistio: asistencia === "presente" ? true : (asistencia === "ausente" ? false : null),
          nota: tr.querySelector(".cap-nota-inp")?.value || null,
        };
      }).filter((r) => r.asistio !== null);
      if (!registros.length) {
        alert("Registrá la asistencia de al menos una persona");
        return;
      }
      try {
        await putJson(`${API}/encuentros/${asistenciaEncuentroId}/cierre`, { personas: registros });
        closeAsistenciaModal();
        if (typeof loadEncuentros === "function") await loadEncuentros();
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

    currentCapView = view;

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

    bindEncAccionModal();

    bindProgramaForm();

    bindRequisitos();

    bindAsistenciaModal();

    bindImportPersonas();



    if (view === "panel") {

      try { await Promise.all([loadDashboard(), loadEncuentros()]); } catch (e) { console.error(e); }

    }

    if (view === "cronograma") {

      try { await Promise.all([loadEncuentros(), loadPuestosOptions(), loadCursos()]); } catch (e) { console.error(e); }

    }

    if (view === "programas") {

      try { await loadCursos(); } catch (e) { console.error(e); }

      try { await loadPuestosOptions(); } catch (e) { console.error(e); }

      try { await loadProgramas(); } catch (e) { console.error(e); }

    }

    if (view === "matriz") {

      try {

        await loadMeta();

        fillSelect("cap-matriz-sector", metaSectores, "Todos los sectores");

        if (matrizParticipanteId) {
          matrizParticipanteNombre = sessionStorage.getItem("cap_matriz_persona_nombre");
          if (matrizParticipanteNombre) {
            sessionStorage.removeItem("cap_matriz_persona_nombre");
          }
          updateMatrizPersonaFilter();
        }

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



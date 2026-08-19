(function () {

  "use strict";



  const API = window.CAP_API_BASE || "/gos/capacitacion/api";

  const MESES = [

    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",

    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",

  ];

  const DOW = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

  function fmtMesProgramado(fechaIso) {
    if (!fechaIso) return "";
    const [yy, mm] = String(fechaIso).slice(0, 7).split("-");
    return `${MESES[Number(mm) - 1] || ""} ${yy}`.trim();
  }

  function fmtDiaReal(iso) {
    if (!iso) return "";
    const p = String(iso).split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : String(iso);
  }



  let calYear = new Date().getFullYear();

  let calMonth = new Date().getMonth();

  let calView = "mes";

  let encuentros = [];
  let encuentrosYearLoaded = null;
  const MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  let currentCapView = "panel";
  let encuentroEditId = null;
  let encAccionEncuentroId = null;

  let metaSectores = [];

  let metaPuestos = [];

  let metaCentros = [];
  let metaClientes = [];
  let personaEditId = null;
  let cursoEditId = null;
  let periodosVigenciaCache = null;
  let asistenciaEncuentroId = null;
  let chartPersonal = null;
  let chartCert = null;
  let chartSector = null;
  let chartTipo = null;
  let chartInforme = null;
  let clienteEditId = null;
  let clienteLogoId = null;
  let isoNormaActual = "9001";
  let personaSeleccionadaId = null;
  let personasCache = [];
  let matrizParticipanteId = window.CAP_INITIAL_PARTICIPANTE_ID || null;
  let matrizParticipanteNombre = null;
  let maVista = "calendario";
  let maResumenDim = "puestos";
  let maTablaAgrupar = "puesto";
  let maFiltros = { planes: [], tipos: [], empresas: [], personas: [], puestos: [], cursos: [] };
  let maFiltrosMeta = null;
  let crVista = "calendario";
  let crResumenDim = "puestos";
  let crFiltros = { planes: [], tipos: [], empresas: [], personas: [], puestos: [], cursos: [] };
  let crFiltrosMeta = null;
  let crDetalleEventos = [];
  let encPlanesCache = [];
  let encProgramasCache = [];
  let certUploadRegistroId = null;
  let taxonomiaCascada = null;
  let taxonomiaListas = null;



  async function fetchJson(url, options) {
    const r = await fetch(url, { credentials: "same-origin", ...options });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      throw new Error(mensajeErrorHttp(r.status, data));
    }
    return data;
  }

  function mensajeErrorHttp(status, data) {
    if (data && data.error) return data.error;
    if (status === 404) {
      return "El servidor no tiene esta función todavía. Cerrá GOS local y volvé a abrirlo con ABRIR LOCAL PRUEBA.bat, después recargá la página.";
    }
    if (status === 403) return "No tenés permiso para esta acción.";
    if (status >= 500) return "Error interno del servidor. Revisá la ventana de GOS local.";
    return `Error de red (${status})`;
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
    if (!r.ok) throw new Error(mensajeErrorHttp(r.status, data));
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



  const SIMILAR_TIPO_LABELS = {
    sector: "sector",
    puesto: "puesto",
    centro: "centro",
    instructor: "capacitador",
    empresa_capacitadora: "empresa capacitadora",
    taxonomia: "clasificación",
    curso: "curso",
  };

  let similarModalResolver = null;



  function hideSimilarModal() {

    document.getElementById("cap-similar-modal")?.classList.add("cap-hidden");

  }



  function bindSimilarModal() {

    const finish = (result) => {

      hideSimilarModal();

      if (similarModalResolver) {

        similarModalResolver(result);

        similarModalResolver = null;

      }

    };

    document.getElementById("cap-similar-cerrar")?.addEventListener("click", () => finish({ action: "cancel" }));

    document.getElementById("cap-similar-backdrop")?.addEventListener("click", () => finish({ action: "cancel" }));

    document.getElementById("cap-similar-cancel")?.addEventListener("click", () => finish({ action: "cancel" }));

    document.getElementById("cap-similar-create")?.addEventListener("click", () => finish({ action: "create" }));

    document.getElementById("cap-similar-use")?.addEventListener("click", () => {

      const selected = document.querySelector(".cap-similar-item.cap-similar-item--selected");

      const id = selected ? Number(selected.dataset.id) : null;

      const item = selected?._similarItem || null;

      if (!item) {

        finish({ action: "cancel" });

        return;

      }

      finish({ action: "use", item });

    });

  }



  function showSimilarModal({ nombre, tipo, similares }) {

    return new Promise((resolve) => {

      const modal = document.getElementById("cap-similar-modal");

      const list = document.getElementById("cap-similar-list");

      const intro = document.getElementById("cap-similar-intro");

      if (!modal || !list || !intro) {

        resolve({ action: "create" });

        return;

      }

      const tipoLabel = SIMILAR_TIPO_LABELS[tipo] || "registro";

      intro.textContent = `«${nombre}» se parece a ${similares.length === 1 ? "un" : "varios"} ${tipoLabel}${similares.length === 1 ? "" : "s"} que ya existen:`;

      list.innerHTML = similares.map((item, idx) => {

        const detalle = [

          item.tipo_label,

          item.codigo ? `Código: ${item.codigo}` : null,

          item.similitud ? `${Math.round(item.similitud * 100)}% similar` : null,

        ].filter(Boolean).join(" · ");

        return `<li><button type="button" class="cap-similar-item${idx === 0 ? " cap-similar-item--selected" : ""}" data-id="${item.id}">

          <strong>${item.nombre}</strong>

          <small>${detalle}</small>

        </button></li>`;

      }).join("");

      list.querySelectorAll(".cap-similar-item").forEach((btn, idx) => {

        btn._similarItem = similares[idx];

        btn.addEventListener("click", () => {

          list.querySelectorAll(".cap-similar-item").forEach((el) => el.classList.remove("cap-similar-item--selected"));

          btn.classList.add("cap-similar-item--selected");

        });

      });

      similarModalResolver = resolve;

      modal.classList.remove("cap-hidden");

    });

  }



  async function resolveSimilarBeforeCreate({ tipo, nombre, codigo, nivel, excludeId }) {

    const params = new URLSearchParams({ tipo, nombre: nombre || "" });

    if (codigo) params.set("codigo", codigo);

    if (nivel) params.set("nivel", nivel);

    if (excludeId) params.set("exclude_id", String(excludeId));

    let similares = [];

    try {

      const data = await fetchJson(`${API}/similares?${params}`);

      similares = data.similares || [];

    } catch (err) {

      console.error(err);

      return { action: "create" };

    }

    if (!similares.length) return { action: "create" };

    return showSimilarModal({ nombre: nombre || codigo, tipo, similares });

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

  function renderClienteChecks(selectedIds) {
    const wrap = document.getElementById("cap-p-clientes");
    if (!wrap) return;
    const selected = new Set((selectedIds || []).map(Number));
    if (!metaClientes.length) {
      wrap.innerHTML = '<p class="cap-muted">Cargá clientes en Cursos y catálogos.</p>';
      return;
    }
    wrap.innerHTML = metaClientes.map((c) => `
      <label class="cap-check-item">
        <input type="checkbox" data-cliente-id="${c.id}" ${selected.has(c.id) ? "checked" : ""}>
        ${escapeHtml(c.nombre)}
      </label>
    `).join("");
  }

  function selectedClienteIds() {
    return [...document.querySelectorAll("#cap-p-clientes input[data-cliente-id]:checked")]
      .map((el) => Number(el.dataset.clienteId))
      .filter(Number.isFinite);
  }

  function nombresClientes(ids) {
    if (!ids || !ids.length) return "";
    const map = new Map(metaClientes.map((c) => [c.id, c.nombre]));
    return ids.map((id) => map.get(id) || `#${id}`).join(", ");
  }

  function renderEmpresaLogoPreview(tiene) {
    const img = document.getElementById("cap-cfg-logo-preview");
    const empty = document.getElementById("cap-cfg-logo-empty");
    const del = document.getElementById("cap-cfg-logo-del");
    if (img) {
      img.classList.toggle("cap-hidden", !tiene);
      if (tiene) img.src = `${API}/configuracion/logo?t=${Date.now()}`;
    }
    empty?.classList.toggle("cap-hidden", !!tiene);
    del?.classList.toggle("cap-hidden", !tiene);
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

    const tipo = prefill?.tipo ?? document.getElementById("cap-c-tipo")?.value ?? "";

    const modalidad = prefill?.modalidad ?? document.getElementById("cap-c-modalidad")?.value ?? "";



    fillCascadeSelect("cap-c-tipo", taxListaEntries("tipos"), "— Seleccionar —", false);

    fillCascadeSelect("cap-c-modalidad", taxListaEntries("modalidades"), "— Seleccionar —", false);



    if (tipo) document.getElementById("cap-c-tipo").value = tipo;

    if (modalidad) document.getElementById("cap-c-modalidad").value = modalidad;

  }



  function bindCursoCascada() {

    document.querySelectorAll(".cap-tax-quick-add").forEach((btn) => {

      btn.addEventListener("click", () => openTaxQuickAdd(btn.dataset.nivel));

    });

  }



  const taxSelected = { tipo: null, modalidad: null };

  const taxItemsCache = { tipo: [], modalidad: [] };

  const TAX_NIVELES = ["tipo", "modalidad"];

  const TAX_NIVEL_LABELS = {
    tipo: "tipo",
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

      tipo: document.getElementById("cap-c-tipo")?.value,

      modalidad: document.getElementById("cap-c-modalidad")?.value,

    });

  }



  function applyTaxSelectionAfterCreate(createdItem) {

    if (!createdItem?.nivel) return;

    taxSelected[createdItem.nivel] = createdItem;

  }



  function taxContextLabel(nivel) {

    const labels = {

      tipo: "Nuevo tipo",

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



    document.getElementById("cap-tax-btn-add-tipo")?.addEventListener("click", () => openTaxAdd("tipo"));

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

          const resolution = await resolveSimilarBeforeCreate({

            tipo: "taxonomia",

            nombre: payload.nombre,

            codigo: payload.codigo,

            nivel,

          });

          if (resolution.action === "cancel") return;

          if (resolution.action === "use") {

            await applyTaxSelectionAfterCreate(resolution.item);

            await reloadTaxonomia();

            const taxSelectIds = {

              tipo: "cap-c-tipo",

              modalidad: "cap-c-modalidad",

            };

            const selectId = taxSelectIds[nivel];

            if (selectId && resolution.item.codigo) {

              document.getElementById(selectId).value = resolution.item.codigo;

            }

          } else {

            const data = await postJson(`${API}/taxonomia/items`, payload);

            await applyTaxSelectionAfterCreate(data.item);

            await reloadTaxonomia();

          }

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

    const [sectores, puestos, centros, clientes] = await Promise.all([
      fetchJson(`${API}/sectores`),
      fetchJson(`${API}/puestos`),
      fetchJson(`${API}/centros`),
      fetchJson(`${API}/clientes`).catch(() => ({ clientes: [] })),
    ]);
    metaSectores = sectores.sectores || [];
    metaPuestos = puestos.puestos || [];
    metaCentros = centros.centros || [];
    metaClientes = clientes.clientes || [];
    const clientesSeleccionados = selectedClienteIds();
    fillSelect("cap-p-sector", metaSectores, "— Sin sector —");
    fillSelect("cap-p-puesto", metaPuestos, "— Sin puesto —");
    fillSelect("cap-p-centro", metaCentros, "— Sin centro —");
    fillSelect("cap-puesto-quick-sector", metaSectores, "— Sin sector —");
    renderClienteChecks(clientesSeleccionados);
  }



  function renderRecursos(data) {

    const tbody = document.getElementById("cap-recursos-body");

    if (!tbody) return;

    tbody.innerHTML = (data.recursos || []).map((r) => {

      const esPersonal = r.clave === "personal";

      const tGreen = esPersonal ? "Habilitados" : "Vigentes";

      const tRed = esPersonal ? "No habilitados (desaprobó o no lo hizo a tiempo)" : "Vencidas";

      const tGray = esPersonal ? "Sin datos" : "Otros";

      return `

      <tr>

        <td>${r.nombre}</td>

        <td>

          <div class="cap-status-group">

            <span class="cap-badge cap-badge--green" title="${tGreen}">${r.verde}</span>

            <span class="cap-badge cap-badge--red" title="${tRed}">${r.rojo}</span>

            <span class="cap-badge cap-badge--gray" title="${tGray}">${r.gris}</span>

          </div>

        </td>

      </tr>

    `;

    }).join("");



    const hab = document.getElementById("cap-habilitados-pct");

    const inh = document.getElementById("cap-inhabilitados-pct");

    if (hab) hab.textContent = `${data.habilitados_pct || 0}%`;

    if (inh) inh.textContent = `${data.inhabilitados_pct || 0}%`;

  }



  function mesKey(year, monthIdx) {
    return `${year}-${pad(monthIdx + 1)}`;
  }

  function encuentrosEnMes(year, monthIdx) {
    const ym = mesKey(year, monthIdx);
    return encuentros.filter((e) => {
      const mesProg = String(e.fecha || "").slice(0, 7);
      const mesReal = String(e.fecha_realizacion || "").slice(0, 7);
      return mesProg === ym || mesReal === ym;
    });
  }

  function encuentrosProgramadosMes(year, monthIdx) {
    const ym = mesKey(year, monthIdx);
    return encuentros.filter((e) => {
      const mesProg = String(e.fecha || "").slice(0, 7);
      if (mesProg !== ym) return false;
      const mesReal = String(e.fecha_realizacion || "").slice(0, 7);
      return !mesReal || mesReal !== ym;
    });
  }

  function encuentrosDelDia(y, m, d) {
    const iso = isoDate(y, m, d);
    return encuentros.filter((e) => e.fecha_realizacion === iso);
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

    renderCalMonthStrip();
    renderCalProgramadosMes();

    document.querySelectorAll("[data-encuentro-id]").forEach((el) => {

      el.addEventListener("click", (ev) => {

        ev.stopPropagation();

        onCalEventClick(Number(el.dataset.encuentroId));

      });

    });

  }

  function renderCalMonthStrip() {
    const counts = MESES_CORTOS.map((_, i) => encuentrosEnMes(calYear, i).length);
    const html = MESES_CORTOS.map((nom, i) => {
      const n = counts[i];
      const active = i === calMonth ? " cap-cal-month-chip--active" : "";
      const has = n > 0 ? " cap-cal-month-chip--has" : "";
      const badge = n > 0 ? `<span class="cap-cal-month-chip-n">${n}</span>` : "";
      return `<button type="button" class="cap-cal-month-chip${active}${has}" data-cal-goto-mes="${i}" title="${MESES[i]} ${calYear}">${nom}${badge}</button>`;
    }).join("");
    ["cap-cal-month-strip", "cap-cal-month-strip-2"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = html;
    });
    document.querySelectorAll("[data-cal-goto-mes]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const m = Number(btn.dataset.calGotoMes);
        if (Number.isNaN(m) || m === calMonth) return;
        calMonth = m;
        loadEncuentros();
      });
    });
  }

  function renderCalProgramadosMes() {
    const items = encuentrosProgramadosMes(calYear, calMonth);
    const html = items.length
      ? `<p class="cap-cal-programados-label">Programados en ${MESES[calMonth]} <span class="cap-muted">(el día aparece al cerrar el cronograma)</span></p>
        ${items.map((e) => {
          const extra = e.fecha_realizacion
            ? ` · Realizado el ${fmtDiaReal(e.fecha_realizacion)}`
            : "";
          return `<button type="button" class="cap-cal-event cap-cal-event--mes${e.estado === "cancelado" ? " cap-cal-event--cancelado" : ""}" data-encuentro-id="${e.id}" title="${escapeHtml(e.titulo)}">${escapeHtml(e.titulo)}${extra}</button>`;
        }).join("")}`
      : "";
    ["cap-cal-programados", "cap-cal-programados-2"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = html;
      el.classList.toggle("cap-hidden", !items.length);
    });
  }



  function onCalEventClick(encuentroId) {

    if (currentCapView === "cronograma") {

      openEncAccionModal(encuentroId).catch(console.error);

      return;

    }

    openAsistenciaModal(encuentroId).catch(console.error);

  }



  async function loadEncuentros(forceReload) {
    if (forceReload) encuentrosYearLoaded = null;
    if (encuentrosYearLoaded !== calYear) {
      const data = await fetchJson(`${API}/encuentros?desde=${calYear}-01-01&hasta=${calYear}-12-31`);
      encuentros = data.encuentros || [];
      encuentrosYearLoaded = calYear;
    }
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

          labels: ["Habilitados", "No habilitados", "Sin datos"],

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



  async function loadMatrizLegacy() {

    const sector = document.getElementById("cap-matriz-sector")?.value || "";

    const estado = document.getElementById("cap-matriz-estado")?.value || "";

    let url = `${API}/matriz?`;

    if (sector) url += `sector_id=${sector}&`;

    if (estado) url += `estado=${estado}&`;

    if (matrizParticipanteId) url += `participante_id=${matrizParticipanteId}&`;

    const data = await fetchJson(url);

    const head = document.getElementById("cap-matriz-head");

    const body = document.getElementById("cap-matriz-body");

    if (!head || !body) return data;

    if (matrizParticipanteId && !matrizParticipanteNombre) {
      const fila = (data.filas || []).find((f) => f.participante_id === matrizParticipanteId);
      if (fila?.nombre) {
        matrizParticipanteNombre = fila.nombre;
      }
    }

    renderMatrizTable(data, head, body);

    return data;

  }

  function maQueryParams() {
    const anio = document.getElementById("cap-ma-anio")?.value || new Date().getFullYear();
    const q = new URLSearchParams({ vista: maVista, anio });
    if (maFiltros.planes.length) q.set("planes", maFiltros.planes.join(","));
    if (maFiltros.tipos.length) q.set("tipos", maFiltros.tipos.join(","));
    if (maFiltros.empresas.length) q.set("empresas", maFiltros.empresas.join(","));
    if (maFiltros.personas.length) q.set("personas", maFiltros.personas.join(","));
    if (maFiltros.puestos.length) q.set("puestos", maFiltros.puestos.join(","));
    if (maFiltros.cursos.length) q.set("cursos", maFiltros.cursos.join(","));
    if (maVista === "calendario") q.set("dim", maResumenDim);
    if (maVista === "tabla") q.set("agrupar_por", maTablaAgrupar);
    if (maVista === "persona") {
      const pid = document.getElementById("cap-ma-persona-select")?.value;
      if (pid) q.set("persona_id", pid);
    }
    return q;
  }

  const CAP_MS_OPTS = {
    planes: { allLabel: "Todos los planes", searchable: false },
    tipos: { allLabel: "Todos los tipos", searchable: false },
    empresas: { allLabel: "Todas las empresas", searchable: true },
    personas: { allLabel: "Todas las personas", searchable: true },
    puestos: { allLabel: "Todos los puestos", searchable: true },
    cursos: { allLabel: "Todos los cursos", searchable: true },
  };

  let capMultiSelectBound = false;

  function bindCapMultiSelectGlobal() {
    if (capMultiSelectBound) return;
    capMultiSelectBound = true;
    document.addEventListener("mousedown", (e) => {
      if (e.target.closest(".cap-multi-select")) return;
      document.querySelectorAll(".cap-multi-panel:not(.cap-hidden)").forEach((panel) => {
        panel.classList.add("cap-hidden");
        panel.closest(".cap-multi-select")?.querySelector(".cap-multi-btn")?.setAttribute("aria-expanded", "false");
      });
    });
  }

  function capMsItemLabel(it, labelKey = "nombre") {
    const label = it[labelKey] || it.nombre || "";
    if (it.legajo) return `${label} (${it.legajo})`;
    if (it.codigo) return `${it.codigo} — ${label}`;
    return label;
  }

  function capMsBtnLabel(items, grupo, selected) {
    const opts = CAP_MS_OPTS[grupo] || { allLabel: "Todos" };
    if (!selected.length) return opts.allLabel;
    if (selected.length === 1) {
      const sid = String(selected[0]);
      const it = (items || []).find((i) => String(i.id) === sid);
      return it ? capMsItemLabel(it) : "1 seleccionado";
    }
    return `${selected.length} seleccionados`;
  }

  function renderCapMultiSelect(containerId, items, grupo, filtros, onChange) {
    bindCapMultiSelectGlobal();
    const el = document.getElementById(containerId);
    if (!el) return;
    const opts = CAP_MS_OPTS[grupo] || { allLabel: "Todos", searchable: true };
    const selected = filtros[grupo] || [];
    const isSelected = (id) => selected.some((s) => String(s) === String(id));
    const btnLabel = capMsBtnLabel(items, grupo, selected);

    el.innerHTML = `
      <button type="button" class="cap-multi-btn" aria-expanded="false" aria-haspopup="listbox">
        <span class="cap-multi-btn-label">${escapeHtml(btnLabel)}</span>
        <span class="cap-multi-chevron" aria-hidden="true">▾</span>
      </button>
      <div class="cap-multi-panel cap-hidden" role="listbox">
        ${opts.searchable ? '<div class="cap-multi-search"><input type="text" class="cap-multi-search-input" placeholder="Buscar..." autocomplete="off"></div>' : ""}
        <div class="cap-multi-toolbar">
          <button type="button" class="cap-multi-link" data-action="all">Seleccionar todos</button>
          <button type="button" class="cap-multi-link" data-action="none">Limpiar</button>
        </div>
        <div class="cap-multi-list">
          ${(items || []).map((it) => {
            const id = it.id;
            const checked = isSelected(id);
            return `<label class="cap-multi-item"><input type="checkbox" value="${escapeHtml(String(id))}"${checked ? " checked" : ""}><span>${escapeHtml(capMsItemLabel(it))}</span></label>`;
          }).join("") || '<p class="cap-multi-empty">Sin opciones</p>'}
        </div>
        <div class="cap-multi-footer"><span class="cap-multi-count">${selected.length} seleccionado(s)</span></div>
      </div>`;

    const btn = el.querySelector(".cap-multi-btn");
    const panel = el.querySelector(".cap-multi-panel");
    const btnLabelEl = el.querySelector(".cap-multi-btn-label");
    const countEl = el.querySelector(".cap-multi-count");

    const syncFromCheckboxes = () => {
      filtros[grupo] = [...el.querySelectorAll(".cap-multi-item input:checked")].map((cb) => cb.value);
      const sel = filtros[grupo];
      btnLabelEl.textContent = capMsBtnLabel(items, grupo, sel);
      countEl.textContent = `${sel.length} seleccionado(s)`;
      onChange();
    };

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const opening = panel.classList.contains("cap-hidden");
      document.querySelectorAll(".cap-multi-panel:not(.cap-hidden)").forEach((p) => {
        if (p !== panel) {
          p.classList.add("cap-hidden");
          p.closest(".cap-multi-select")?.querySelector(".cap-multi-btn")?.setAttribute("aria-expanded", "false");
        }
      });
      panel.classList.toggle("cap-hidden");
      btn.setAttribute("aria-expanded", String(opening));
      if (opening) el.querySelector(".cap-multi-search-input")?.focus();
    });

    panel.querySelectorAll(".cap-multi-link").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        if (link.dataset.action === "all") {
          filtros[grupo] = (items || []).map((it) => String(it.id));
          el.querySelectorAll(".cap-multi-item input").forEach((cb) => { cb.checked = true; });
        } else {
          filtros[grupo] = [];
          el.querySelectorAll(".cap-multi-item input").forEach((cb) => { cb.checked = false; });
        }
        btnLabelEl.textContent = capMsBtnLabel(items, grupo, filtros[grupo]);
        countEl.textContent = `${filtros[grupo].length} seleccionado(s)`;
        onChange();
      });
    });

    el.querySelectorAll(".cap-multi-item input").forEach((cb) => {
      cb.addEventListener("change", syncFromCheckboxes);
    });

    const searchInput = el.querySelector(".cap-multi-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        const q = searchInput.value.toLowerCase().trim();
        el.querySelectorAll(".cap-multi-item").forEach((label) => {
          const text = label.textContent.toLowerCase();
          label.classList.toggle("cap-hidden", q && !text.includes(q));
        });
      });
      searchInput.addEventListener("click", (e) => e.stopPropagation());
    }
  }

  function renderMaPills(containerId, items, grupo) {
    renderCapMultiSelect(containerId, items, grupo, maFiltros, () => {
      loadMatrizAnalitica().catch(console.error);
    });
  }

  function maFmtPct(val) {
    if (val === null || val === undefined || val === "") return "0,0%";
    const n = typeof val === "number" ? val : parseFloat(val);
    if (Number.isNaN(n)) return "—";
    return `${(n * 100).toFixed(1).replace(".", ",")}%`;
  }

  function maFmtRatio(val) {
    if (val === null || val === undefined || val === "") return "0";
    if (typeof val === "number" && val > 0 && val <= 1) return maFmtPct(val);
    if (typeof val === "number") return String(Math.round(val));
    return val;
  }

  function maFmtCount(val) {
    if (val === null || val === undefined || val === "") return "0";
    if (typeof val === "number") return String(Math.round(val));
    return val;
  }

  function applyResumenDimHighlight(rootSelector, dim) {
    const root = document.querySelector(rootSelector);
    if (!root) return;
    root.querySelectorAll(".cap-ma-filtro-grupo").forEach((g) => {
      const grupo = g.dataset.grupo;
      const destacado =
        (dim === "puestos" && grupo === "puestos") ||
        (dim === "planes" && grupo === "planes") ||
        (dim === "cursos" && (grupo === "tipos" || grupo === "cursos")) ||
        (dim === "personas" && (grupo === "personas" || grupo === "puestos"));
      g.classList.toggle("cap-ma-filtro-grupo--destacado", destacado);
    });
  }

  function applyMaResumenDimHighlight() {
    applyResumenDimHighlight("#cap-ma-filtros", maResumenDim);
  }

  function renderResumenMensualTable(wrap, data, dim, { filtroRoot, onDimChange, onOpenDetalle }) {
    if (!wrap) return;
    const filas = data.filas || [];
    const tot = data.totales || {};
    const anio = data.anio || "";
    const colNom = {
      puestos: ["Puestos Programados", "Puestos Pendientes", "Puestos Cumplidos"],
      planes: ["Planes Programados", "Planes Pendientes", "Planes Cumplidos"],
      cursos: ["Cursos Programados", "Cursos Pendientes", "Cursos Cumplidos"],
      personas: ["Personas Programadas", "Personas Pendientes", "Personas Cumplidas"],
    }[dim] || ["Cursos Programados", "Cursos Pendientes", "Cursos Cumplidos"];
    const countCols = [
      ["programados", colNom[0], "cap-ma-val--programados", "cap-ma-resumen-th--prog", 1],
      ["pendientes", colNom[1], "cap-ma-val--pendientes", "cap-ma-resumen-th--metric", 1],
      ["cumplidos", colNom[2], "cap-ma-val--cumplidos", "cap-ma-resumen-th--metric", 1],
      ["pct_cumpl_prog", "% Cumpl./Pr.", "cap-ma-val--pct", "cap-ma-resumen-th--metric", 1],
      ["charlas_puntuales", "Puntuales", "cap-ma-val--charlas-puntuales", "cap-ma-resumen-th--puntuales", 1],
      ["pend_vencidos", "Pendientes Vencidos", "cap-ma-val--vencidos", "cap-ma-resumen-th--metric", 1],
      ["pct_venc_prog", "% Venc./Pr.", "cap-ma-val--pct", "cap-ma-resumen-th--metric", 1],
    ];
    const pctCols = [
      ["pct_pend_sin_vencer", "Pendientes Sin Vencer", "cap-ma-val--pend-sin-vencer", "cap-ma-resumen-th--pct-blue"],
      ["pct_pend_vencidos", "Pendientes Vencidos", "cap-ma-val--vencidos", "cap-ma-resumen-th--pct-red"],
      ["pct_cumpl_puntuales", "Cumplidos Puntuales", "cap-ma-val--puntuales", "cap-ma-resumen-th--pct-green"],
      ["pct_cumpl_no_puntuales", "Cumplidos No Puntuales", "cap-ma-val--cumplidos", "cap-ma-resumen-th--pct-purple"],
    ];
    const allCols = [...countCols, ...pctCols];
    const dims = [
      ["puestos", "Puestos"],
      ["personas", "Personas"],
      ["planes", "Planes"],
      ["cursos", "Cursos"],
    ];
    const dimLabels = { puestos: "Puesto", planes: "Plan", cursos: "Curso", personas: "Persona" };
    const rowHead = dimLabels[dim] || "";
    const cellVal = (row, key) => (key.startsWith("pct_") ? maFmtPct(row[key]) : maFmtCount(row[key]));
    const rowCells = (row) => allCols.map(([k, lbl, cls]) => {
      const mes = row.mes || row.id;
      return `<td class="cap-ma-num ${cls} cap-ma-cell--clickable" data-ma-mes="${mes}" data-ma-metric="${k}" data-ma-label="${escapeHtml(lbl)}" tabindex="0" role="button" title="Clic para ver el detalle">${cellVal(row, k)}</td>`;
    }).join("");
    const totalCells = allCols.map(([k, , cls]) =>
      `<td class="cap-ma-num cap-ma-total-cell ${cls}">${cellVal(tot, k)}</td>`
    ).join("");
    const bodyRows = filas.length
      ? filas.map((f) =>
          `<tr><th scope="row" class="cap-ma-mes-cell cap-ma-cell--clickable" data-ma-mes="${f.mes || f.id}" data-ma-metric="programados" data-ma-label="${escapeHtml(colNom[0])}" tabindex="0" role="button" title="Clic para ver el detalle">${escapeHtml(f.nombre)}</th>${rowCells(f)}</tr>`
        ).join("")
      : `<tr><td colspan="${allCols.length + 1}" class="cap-empty">Sin datos para este ámbito</td></tr>`;
    wrap.innerHTML = `
      <div class="cap-ma-resumen-wrap">
        <div class="cap-ma-resumen-dims" role="tablist" aria-label="Ámbito del resumen">
          ${dims.map(([id, lbl]) =>
            `<button type="button" role="tab" aria-selected="${dim === id}" class="cap-ma-resumen-dim${dim === id ? " active" : ""}" data-resumen-dim="${id}">${lbl}</button>`
          ).join("")}
        </div>
        <div class="cap-ma-table-scroll cap-ma-resumen-scroll">
          <table class="cap-data-table cap-ma-resumen-table">
            <thead>
              <tr>
                <th rowspan="2" class="cap-ma-resumen-anio">${escapeHtml(String(anio))}${rowHead ? `<span class="cap-ma-resumen-dim-sub">${escapeHtml(rowHead)}</span>` : ""}</th>
                <th rowspan="2" class="cap-ma-resumen-th cap-ma-resumen-th--prog">${escapeHtml(colNom[0])}</th>
                <th colspan="3" class="cap-ma-resumen-th cap-ma-resumen-th--metric">Cumplimiento</th>
                <th rowspan="2" class="cap-ma-resumen-th cap-ma-resumen-th--puntuales">Puntuales</th>
                <th colspan="2" class="cap-ma-resumen-th cap-ma-resumen-th--metric">Vencidos</th>
                <th colspan="4" class="cap-ma-resumen-th cap-ma-resumen-th--pct-group">Distribución %</th>
              </tr>
              <tr>
                ${countCols.slice(1).filter(([k]) => k !== "charlas_puntuales").map(([, lbl, , thCls]) =>
                  `<th class="cap-ma-resumen-th ${thCls}">${escapeHtml(lbl)}</th>`
                ).join("")}
                ${pctCols.map(([, lbl, , thCls]) =>
                  `<th class="cap-ma-resumen-th ${thCls}">${escapeHtml(lbl)}</th>`
                ).join("")}
              </tr>
            </thead>
            <tbody>
              ${bodyRows}
              <tr class="cap-ma-total-row">
                <th scope="row" class="cap-ma-mes-cell cap-ma-mes-cell--total">Total</th>
                ${totalCells}
              </tr>
            </tbody>
          </table>
        </div>
      </div>`;
    wrap.querySelectorAll("[data-resumen-dim]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.dataset.resumenDim || "puestos";
        if (next === dim) return;
        wrap.innerHTML = '<p class="cap-loading">Cargando...</p>';
        onDimChange(next);
      });
    });
    applyResumenDimHighlight(filtroRoot, dim);
    wrap.querySelectorAll("[data-ma-mes]").forEach((el) => {
      const handler = () => onOpenDetalle(el);
      el.addEventListener("click", handler);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); handler(); }
      });
    });
  }

  function renderMaCalendario(data) {
    renderResumenMensualTable(
      document.getElementById("cap-ma-vista-calendario"),
      data,
      data.dim || maResumenDim,
      {
        filtroRoot: "#cap-ma-filtros",
        onDimChange: (next) => {
          maResumenDim = next;
          loadMatrizAnalitica().catch(console.error);
        },
        onOpenDetalle: (el) => openResumenCeldaDetalle(el, maQueryParams(), maResumenDim).catch(console.error),
      }
    );
  }

  async function openResumenCeldaDetalle(el, q, dim) {
    const mes = Number(el.dataset.maMes);
    const metrica = el.dataset.maMetric || "programados";
    const label = el.dataset.maLabel || "";
    if (!mes) return;
    q.delete("vista");
    q.delete("agrupar_por");
    q.set("nivel", "detalle");
    q.set("mes", String(mes));
    q.set("metrica", metrica);
    q.set("dim", dim);
    const data = await fetchJson(`${API}/matriz/resumen?${q}`);
    const mesNombre = MESES[mes - 1] || "";
    openMaResumenDetalle(data, [mesNombre, label].filter(Boolean).join(" · "), dim);
  }

  function crQueryParams() {
    const anio = document.getElementById("cap-cr-anio")?.value || new Date().getFullYear();
    const q = new URLSearchParams({ vista: "calendario", anio, dim: crResumenDim });
    if (crFiltros.planes.length) q.set("planes", crFiltros.planes.join(","));
    if (crFiltros.tipos.length) q.set("tipos", crFiltros.tipos.join(","));
    if (crFiltros.empresas.length) q.set("empresas", crFiltros.empresas.join(","));
    if (crFiltros.personas.length) q.set("personas", crFiltros.personas.join(","));
    if (crFiltros.puestos.length) q.set("puestos", crFiltros.puestos.join(","));
    if (crFiltros.cursos.length) q.set("cursos", crFiltros.cursos.join(","));
    return q;
  }

  function renderCrPills(containerId, items, grupo) {
    renderCapMultiSelect(containerId, items, grupo, crFiltros, () => {
      loadCronogramaResumen().catch(console.error);
    });
  }

  function personasUnicasDeEventos(eventos) {
    const map = new Map();
    (eventos || []).forEach((ev) => {
      (ev.personas || []).forEach((p) => {
        const id = p.persona_id != null ? String(p.persona_id) : (p.nombre || "");
        if (!id || map.has(id)) return;
        map.set(id, p);
      });
    });
    return [...map.values()].sort((a, b) => (a.nombre || "").localeCompare(b.nombre || "", "es"));
  }

  function openMaResumenDetalle(data, tituloTxt, dim) {
    const modal = document.getElementById("cap-ma-evento-modal");
    const body = document.getElementById("cap-ma-evento-body");
    const titulo = document.getElementById("cap-ma-evento-titulo");
    if (!modal || !body) return;
    crDetalleEventos = data.eventos || [];
    if (titulo) titulo.textContent = tituloTxt || "Detalle";
    if (!crDetalleEventos.length) {
      body.innerHTML = '<p class="cap-empty">Sin cronogramas para esta selección</p>';
    } else if (dim === "personas") {
      const personas = personasUnicasDeEventos(crDetalleEventos);
      body.innerHTML = personas.length
        ? `<ul class="cap-ma-detalle-personas">${personas.map((p) =>
            `<li>${escapeHtml(p.nombre || "")}</li>`
          ).join("")}</ul>`
        : '<p class="cap-empty">Sin personas para esta selección</p>';
    } else if (dim === "planes" || dim === "cursos") {
      body.innerHTML = crDetalleEventos.map((ev) =>
        `<div class="cap-ma-evento cap-ma-evento--detalle cap-ma-evento--static">
          <strong>${escapeHtml(ev.curso_nombre || "Curso")}</strong>
          <span class="cap-muted">${escapeHtml(ev.fecha_realizacion ? fmtDiaReal(ev.fecha_realizacion) : fmtMesProgramado(ev.fecha))}${ev.plan_nombre ? ` · ${escapeHtml(ev.plan_nombre)}` : ""}</span>
        </div>`
      ).join("");
    } else {
      body.innerHTML = crDetalleEventos.map((ev, i) => {
        const n = (ev.personas || []).length;
        return `<button type="button" class="cap-ma-evento cap-ma-evento--detalle" data-cr-ev-idx="${i}">
          <strong>${escapeHtml(ev.curso_nombre || "Curso")}</strong>
          <span class="cap-muted">${escapeHtml(ev.fecha_realizacion ? fmtDiaReal(ev.fecha_realizacion) : fmtMesProgramado(ev.fecha))} · ${escapeHtml(ev.plan_nombre || "")} · ${n} persona(s)</span>
        </button>`;
      }).join("");
      body.querySelectorAll("[data-cr-ev-idx]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const ev = crDetalleEventos[Number(btn.dataset.crEvIdx)];
          if (ev) openMaEventoModal(ev);
        });
      });
    }
    modal.classList.remove("cap-hidden");
  }

  function renderCrResumenTable(data) {
    renderResumenMensualTable(
      document.getElementById("cap-cr-resumen-content"),
      data,
      data.dim || crResumenDim,
      {
        filtroRoot: "#cap-cr-filtros",
        onDimChange: (next) => {
          crResumenDim = next;
          loadCronogramaResumen().catch(console.error);
        },
        onOpenDetalle: (el) => openResumenCeldaDetalle(el, crQueryParams(), crResumenDim).catch(console.error),
      }
    );
  }

  async function loadCronogramaResumen() {
    if (!crFiltrosMeta) {
      crFiltrosMeta = await fetchJson(`${API}/matriz/filtros`);
      renderCrPills("cap-cr-pills-planes", crFiltrosMeta.planes, "planes");
      renderCrPills("cap-cr-pills-tipos", crFiltrosMeta.tipos, "tipos");
      renderCrPills("cap-cr-pills-empresas", crFiltrosMeta.empresas, "empresas");
      renderCrPills("cap-cr-pills-personas", crFiltrosMeta.personas, "personas");
      renderCrPills("cap-cr-pills-puestos", crFiltrosMeta.puestos, "puestos");
      renderCrPills("cap-cr-pills-cursos", crFiltrosMeta.cursos, "cursos");
    }
    const anioSel = document.getElementById("cap-cr-anio");
    if (anioSel && !anioSel.options.length) {
      const y = new Date().getFullYear();
      for (let i = y - 2; i <= y + 1; i++) {
        anioSel.innerHTML += `<option value="${i}"${i === y ? " selected" : ""}>${i}</option>`;
      }
    }
    const wrap = document.getElementById("cap-cr-resumen-content");
    if (wrap) wrap.innerHTML = '<p class="cap-loading">Cargando...</p>';
    const resp = await fetchJson(`${API}/matriz?${crQueryParams()}`);
    renderCrResumenTable(resp.data || resp);
  }

  function bindCronogramaResumen() {
    document.querySelectorAll("#cap-cr-tabs .cap-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        crVista = tab.dataset.crVista || "calendario";
        document.querySelectorAll("#cap-cr-tabs .cap-tab").forEach((t) => t.classList.toggle("active", t === tab));
        document.querySelectorAll(".cap-cr-vista").forEach((v) => v.classList.add("cap-hidden"));
        const anioSel = document.getElementById("cap-cr-anio");
        if (crVista === "resumen") {
          document.getElementById("cap-cr-vista-resumen")?.classList.remove("cap-hidden");
          anioSel?.classList.remove("cap-hidden");
          loadCronogramaResumen().catch(console.error);
        } else {
          document.getElementById("cap-cr-vista-calendario")?.classList.remove("cap-hidden");
          anioSel?.classList.add("cap-hidden");
        }
      });
    });
    document.getElementById("cap-cr-anio")?.addEventListener("change", () => {
      loadCronogramaResumen().catch(console.error);
    });
  }

  function openMaEventoModal(ev) {
    const modal = document.getElementById("cap-ma-evento-modal");
    const body = document.getElementById("cap-ma-evento-body");
    const titulo = document.getElementById("cap-ma-evento-titulo");
    if (!modal || !body) return;
    if (titulo) titulo.textContent = ev.curso_nombre || "Cronograma";
    const emp = ev.empresa_nombre ? ev.empresa_nombre : "GOS Interno";
    const filas = (ev.personas || []).map((p) => {
      const est = p.aprobo === true ? "Aprobó" : (p.aprobo === false ? (p.asistio ? "No aprobó" : "No asistió") : "Pendiente");
      return `<tr><td>${escapeHtml(p.nombre || "")}</td><td>${p.asistio ? "Sí" : "No"}</td><td>${p.nota ?? "—"}</td><td>${est}</td></tr>`;
    }).join("");
    body.innerHTML = `
      <p><strong>Plan:</strong> ${escapeHtml(ev.plan_nombre || "—")} · <strong>Empresa:</strong> ${escapeHtml(emp)}</p>
      <p><strong>Mes programado:</strong> ${escapeHtml(fmtMesProgramado(ev.fecha))}${ev.fecha_realizacion ? ` · <strong>Realizado:</strong> ${escapeHtml(fmtDiaReal(ev.fecha_realizacion))}` : ""} · <strong>Capacitador:</strong> ${escapeHtml(ev.capacitador || "—")}</p>
      <p><strong>Lugar:</strong> ${escapeHtml(ev.lugar || "—")} · <strong>Link:</strong> ${ev.link ? `<a href="${escapeHtml(ev.link)}" target="_blank" rel="noopener">${escapeHtml(ev.link)}</a>` : "—"}</p>
      <table class="cap-data-table cap-mt"><thead><tr><th>Persona</th><th>Asistió</th><th>Nota</th><th>Estado</th></tr></thead><tbody>${filas || '<tr><td colspan="4" class="cap-empty">Sin personas</td></tr>'}</tbody></table>`;
    modal.classList.remove("cap-hidden");
  }

  function estadoLabel(est) {
    const map = { aprobada: "Aprobada", pendiente: "Pendiente", vencida: "Pendiente", no_aprobo: "No aprobó" };
    return map[est] || est;
  }

  function maTablaAgruparButtons(agrupar) {
    return [
      ["puesto", "Puestos"],
      ["persona", "Personas"],
      ["plan", "Planes"],
      ["curso", "Cursos"],
    ].map(([id, lbl]) =>
      `<button type="button" role="tab" class="cap-ma-resumen-dim${agrupar === id ? " active" : ""}" data-ma-agrupar="${id}">${lbl}</button>`
    ).join("");
  }

  function renderMaTabla(data) {
    const wrap = document.getElementById("cap-ma-vista-tabla");
    if (!wrap) return;
    const filas = data.filas || [];
    const meses = data.meses || [];
    const anio = data.anio || "";
    const agrupar = maTablaAgrupar || data.agrupar_por || "persona";
    const subs = ["Prog", "Pdtes", "Cumpl", "Cumpl/Prog"];
    const subKeys = ["prog", "pdtes", "cumpl", "cumpl_prog"];
    const rowLabel = { puesto: "Puesto", curso: "Curso", plan: "Plan" }[agrupar] || "Persona";
    const fmtCell = (k, v) => (k === "cumpl_prog" ? maFmtPct(v) : maFmtCount(v));
    if (!filas.length) {
      wrap.innerHTML = `
        <div class="cap-ma-resumen-wrap">
          <div class="cap-ma-tabla-agrupar cap-ma-resumen-dims" role="tablist" aria-label="Agrupar filas por">
            ${maTablaAgruparButtons(agrupar)}
          </div>
          <p class="cap-empty cap-ma-tabla-empty">Sin datos para los filtros seleccionados</p>
        </div>`;
      bindMaTablaAgrupar();
      return;
    }
    const mesHead = meses.map((m) => `<th colspan="4" class="cap-ma-tabla-mes">${escapeHtml(m.nombre)}</th>`).join("");
    const subHead = [...meses, { num: "anual" }].map((m, idx) =>
      subs.map((s, si) => {
        const cls = si === 2 ? " cap-ma-tabla-comp" : (m.num === "anual" ? " cap-ma-tabla-anual-sub" : "");
        return `<th class="cap-ma-tabla-sub${cls}">${s}</th>`;
      }).join("")
    ).join("");
    const filaHtml = filas.map((f) => {
      const md = f.meses || {};
      const nombre = f.nombre || f.persona || "";
      const celdas = meses.map((m) => {
        const v = md[String(m.num)] || {};
        return subKeys.map((k, si) => {
          const cls = si === 2 ? " cap-ma-tabla-comp" : "";
          const label = `${nombre} · ${subs[si]}`;
          return `<td class="cap-ma-num${cls} cap-ma-cell--clickable" data-ma-tabla-id="${f.id}" data-ma-tabla-mes="${m.num}" data-ma-tabla-metric="${k}" data-ma-tabla-label="${escapeHtml(label)}" tabindex="0" role="button" title="Clic para ver el detalle">${fmtCell(k, v[k])}</td>`;
        }).join("");
      }).join("");
      const anual = md.anual || {};
      const anualCells = subKeys.map((k, si) => {
        const cls = ` cap-ma-anual${si === 2 ? " cap-ma-tabla-comp" : ""}`;
        return `<td class="cap-ma-num${cls}">${fmtCell(k, anual[k])}</td>`;
      }).join("");
      return `<tr><th scope="row" class="cap-ma-persona-col">${escapeHtml(nombre)}</th>${celdas}${anualCells}</tr>`;
    }).join("");
    wrap.innerHTML = `
      <div class="cap-ma-resumen-wrap">
        <div class="cap-ma-tabla-agrupar cap-ma-resumen-dims" role="tablist" aria-label="Agrupar filas por">
          ${maTablaAgruparButtons(agrupar)}
        </div>
        <div class="cap-ma-table-scroll cap-ma-resumen-scroll">
          <table class="cap-data-table cap-ma-tabla-anual">
            <thead>
              <tr>
                <th rowspan="2" class="cap-ma-persona-col cap-ma-tabla-row-label">${escapeHtml(rowLabel)}</th>
                ${mesHead}
                <th colspan="4" class="cap-ma-tabla-mes cap-ma-tabla-mes--anual">Anual</th>
              </tr>
              <tr>${subHead}</tr>
            </thead>
            <tbody>${filaHtml}</tbody>
          </table>
        </div>
      </div>`;
    bindMaTablaAgrupar();
    wrap.querySelectorAll("[data-ma-tabla-mes]").forEach((el) => {
      const handler = () => maOpenTablaDetalle(el).catch(console.error);
      el.addEventListener("click", handler);
      el.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); handler(); }
      });
    });
  }

  async function maOpenTablaDetalle(el) {
    const mes = Number(el.dataset.maTablaMes);
    const rowId = Number(el.dataset.maTablaId);
    const sub = el.dataset.maTablaMetric || "prog";
    const label = el.dataset.maTablaLabel || "";
    if (!mes) return;
    const metricMap = { prog: "programados", pdtes: "pendientes", cumpl: "cumplidos", cumpl_prog: "cumplidos" };
    const dimMap = { persona: "personas", curso: "cursos", plan: "planes", puesto: "personas" };
    const agrupar = maTablaAgrupar || "persona";
    const dim = dimMap[agrupar] || "personas";
    const q = maQueryParams();
    q.delete("vista");
    q.delete("agrupar_por");
    q.set("nivel", "detalle");
    q.set("mes", String(mes));
    q.set("metrica", metricMap[sub] || "programados");
    q.set("dim", dim);
    if (agrupar === "curso") q.set("curso_id", String(rowId));
    if (agrupar === "persona") q.set("persona_id", String(rowId));
    if (agrupar === "plan") q.set("plan_id", String(rowId));
    if (agrupar === "puesto") q.set("puestos", String(rowId));
    const data = await fetchJson(`${API}/matriz/resumen?${q}`);
    const mesNombre = MESES[mes - 1] || "";
    openMaResumenDetalle(data, [mesNombre, label].filter(Boolean).join(" · "), dim);
  }

  function bindMaTablaAgrupar() {
    document.querySelectorAll("#cap-ma-vista-tabla [data-ma-agrupar]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.dataset.maAgrupar || "persona";
        if (next === maTablaAgrupar) return;
        maTablaAgrupar = next;
        document.querySelectorAll("#cap-ma-vista-tabla [data-ma-agrupar]").forEach((b) => {
          b.classList.toggle("active", b.dataset.maAgrupar === maTablaAgrupar);
        });
        loadMatrizAnalitica().catch(console.error);
      });
    });
  }

  function renderMaPersona(data) {
    const wrap = document.getElementById("cap-ma-persona-content");
    if (!wrap) return;
    const p = data.persona || {};
    const m = data.metricas || {};
    const iniciales = (p.nombre || "?").split(" ").map((x) => x[0]).slice(0, 2).join("").toUpperCase();
    const cards = (data.programas || []).map((prog) => {
      const cursos = (prog.cursos || []).map((c) =>
        `<tr><td>${escapeHtml(c.curso)}</td><td>${c.hs}</td><td>${c.nota ?? "—"}</td><td>${estadoLabel(c.estado)}</td><td>${escapeHtml(c.empresa || "GOS Interno")}</td></tr>`
      ).join("");
      return `<div class="cap-ma-programa-card"><h4>${escapeHtml(prog.programa_nombre)}</h4>
        <div class="cap-ma-progreso"><div class="cap-ma-progreso-bar cap-ma-progreso-bar--${(prog.progreso?.porcentaje || 0) >= 100 ? "verde" : (prog.progreso?.porcentaje || 0) >= 50 ? "ambar" : "rojo"}" style="width:${Math.min(prog.progreso?.porcentaje || 0, 100)}%"></div></div>
        <table class="cap-data-table cap-mt"><thead><tr><th>Curso</th><th>Hs</th><th>Nota</th><th>Estado</th><th>Empresa</th></tr></thead><tbody>${cursos}</tbody></table></div>`;
    }).join("");
    const bpcItems = data.buenas_practicas || [];
    const bpcCard = bpcItems.length
      ? `<div class="cap-ma-programa-card"><h4>Buenas Prácticas Compartidas</h4>
        <p class="cap-muted">Capacitaciones complementarias (charlas)</p>
        <table class="cap-data-table cap-mt"><thead><tr><th>Charla</th><th>Hs</th><th>Estado</th><th>Fecha</th></tr></thead><tbody>
        ${bpcItems.map((c) => `<tr><td>${escapeHtml(c.curso)}</td><td>${c.hs || "—"}</td><td>${estadoLabel(c.estado)}</td><td>${c.fecha_aprobacion ? escapeHtml(c.fecha_aprobacion) : "—"}</td></tr>`).join("")}
        </tbody></table></div>`
      : "";
    wrap.innerHTML = `
      <div class="cap-ma-persona-header"><div class="cap-ma-avatar">${iniciales}</div><div><h3>${escapeHtml(p.nombre || "")}</h3><p class="cap-muted">${escapeHtml(p.puesto || "Sin puesto")}</p></div></div>
      <div class="cap-ma-metricas">
        <div class="cap-ma-metrica"><div class="cap-ma-metrica-val">${m.horas_completadas || 0}/${m.horas_requeridas || 0}</div><div class="cap-ma-metrica-lbl">Horas</div></div>
        <div class="cap-ma-metrica"><div class="cap-ma-metrica-val">${m.porcentaje || 0}%</div><div class="cap-ma-metrica-lbl">Cumplimiento</div></div>
        <div class="cap-ma-metrica"><div class="cap-ma-metrica-val">${m.materias_aprobadas || 0}/${m.materias_totales || 0}</div><div class="cap-ma-metrica-lbl">Materias</div></div>
      </div>${cards || '<p class="cap-empty">Sin planes de carrera asignados al puesto actual</p>'}${bpcCard}`;
  }

  async function loadMatrizAnalitica() {
    if (!maFiltrosMeta) {
      maFiltrosMeta = await fetchJson(`${API}/matriz/filtros`);
      const meta = maFiltrosMeta;
      renderMaPills("cap-ma-pills-planes", meta.planes, "planes");
      renderMaPills("cap-ma-pills-tipos", meta.tipos, "tipos");
      renderMaPills("cap-ma-pills-empresas", meta.empresas, "empresas");
      renderMaPills("cap-ma-pills-personas", meta.personas, "personas");
      renderMaPills("cap-ma-pills-puestos", meta.puestos, "puestos");
      renderMaPills("cap-ma-pills-cursos", meta.cursos, "cursos");
      fillSelect("cap-ma-persona-select", meta.personas, "— Seleccionar persona —");
      if (matrizParticipanteId) {
        const sel = document.getElementById("cap-ma-persona-select");
        if (sel) sel.value = String(matrizParticipanteId);
      }
    } else {
      applyMaResumenDimHighlight();
    }
    const anioSel = document.getElementById("cap-ma-anio");
    if (anioSel && !anioSel.options.length) {
      const y = new Date().getFullYear();
      for (let i = y - 1; i <= y + 1; i++) {
        anioSel.add(new Option(String(i), String(i), i === y, i === y));
      }
    }
    if (maVista === "persona" && !document.getElementById("cap-ma-persona-select")?.value) {
      document.getElementById("cap-ma-vista-persona")?.classList.remove("cap-hidden");
      return;
    }
    const resp = await fetchJson(`${API}/matriz?${maQueryParams()}`);
    const payload = resp.data || resp;
    if (maVista === "calendario") renderMaCalendario(payload);
    else if (maVista === "tabla") renderMaTabla(payload);
    else renderMaPersona(payload);
  }

  async function initMatrizAnalitica() {
    maFiltros = { planes: [], tipos: [], empresas: [], personas: [], puestos: [], cursos: [] };
    if (matrizParticipanteId) {
      maFiltros.personas = [String(matrizParticipanteId)];
      maVista = "persona";
      document.querySelectorAll("#cap-ma-tabs .cap-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.maVista === "persona");
      });
      document.querySelectorAll(".cap-ma-vista").forEach((v) => v.classList.add("cap-hidden"));
      document.getElementById("cap-ma-vista-persona")?.classList.remove("cap-hidden");
    }
    if (maFiltrosMeta) {
      renderMaPills("cap-ma-pills-planes", maFiltrosMeta.planes, "planes");
      renderMaPills("cap-ma-pills-tipos", maFiltrosMeta.tipos, "tipos");
      renderMaPills("cap-ma-pills-empresas", maFiltrosMeta.empresas, "empresas");
      renderMaPills("cap-ma-pills-personas", maFiltrosMeta.personas, "personas");
      renderMaPills("cap-ma-pills-puestos", maFiltrosMeta.puestos, "puestos");
      renderMaPills("cap-ma-pills-cursos", maFiltrosMeta.cursos, "cursos");
    }
    await loadMatrizAnalitica();
  }

  async function loadMatriz() {
    await loadMatrizAnalitica();
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
  let programaSeleccionadoGrupoPuestoId = "";
  let programaDetalleEditable = false;
  let programasCache = [];
  let progFiltros = { puestos: [] };
  let progFiltroPuestoKey = "";
  let progPlanesDraft = [];
  let progPlanCatalogCache = [];
  let progNombreCatalogCache = [];

  function refreshProgramaCursoSelect() {

    const all = window.capCursosCache || [];

    const available = all.filter((c) => !programaCursosIds.includes(c.id));

    fillSelect(

      "cap-req-curso",

      available.map((c) => ({ id: c.id, codigo: c.codigo, nombre: c.nombre })),

      available.length ? "— Seleccionar curso —" : "— Todos los cursos ya están en el plan de carrera —"

    );

  }



  function bindMatriz() {
    document.querySelectorAll("#cap-ma-tabs .cap-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        maVista = tab.dataset.maVista || "calendario";
        document.querySelectorAll("#cap-ma-tabs .cap-tab").forEach((t) => t.classList.toggle("active", t === tab));
        document.querySelectorAll(".cap-ma-vista").forEach((v) => v.classList.add("cap-hidden"));
        const map = { calendario: "cap-ma-vista-calendario", tabla: "cap-ma-vista-tabla", persona: "cap-ma-vista-persona" };
        document.getElementById(map[maVista])?.classList.remove("cap-hidden");
        loadMatrizAnalitica().catch(console.error);
      });
    });
    document.getElementById("cap-ma-anio")?.addEventListener("change", () => loadMatrizAnalitica().catch(console.error));
    document.getElementById("cap-ma-persona-select")?.addEventListener("change", () => loadMatrizAnalitica().catch(console.error));
    document.getElementById("cap-matriz-export")?.addEventListener("click", (e) => {
      e.preventDefault();
      window.location.href = `${API}/matriz/exportar.xlsx?${maQueryParams()}`;
    });
    ["cap-ma-evento-cerrar", "cap-ma-evento-backdrop"].forEach((id) => {
      document.getElementById(id)?.addEventListener("click", () => {
        document.getElementById("cap-ma-evento-modal")?.classList.add("cap-hidden");
      });
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
    renderEmpresaLogoPreview(!!cfg.tiene_logo_empresa);
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

    document.getElementById("cap-cfg-logo-btn")?.addEventListener("click", () => {
      document.getElementById("cap-cfg-logo-file")?.click();
    });
    document.getElementById("cap-cfg-logo-file")?.addEventListener("change", async (ev) => {
      const file = ev.target.files?.[0];
      ev.target.value = "";
      if (!file) return;
      try {
        await uploadFile(`${API}/configuracion/logo`, file);
        await loadConfig();
      } catch (e) {
        const logoErr = document.getElementById("cap-config-error");
        if (logoErr) logoErr.textContent = e.message;
      }
    });
    document.getElementById("cap-cfg-logo-del")?.addEventListener("click", async () => {
      try {
        await deleteJson(`${API}/configuracion/logo`);
        await loadConfig();
      } catch (e) {
        const logoErr = document.getElementById("cap-config-error");
        if (logoErr) logoErr.textContent = e.message;
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

                ${r.titulo}<small>${r.subtitulo || (r.tipo === "programa" ? "Plan de carrera" : r.tipo)}</small>

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



  let encPuestosSeleccionados = new Set();
  let encPersonasCache = [];



  function getEncPuestosSeleccionados() {

    return Array.from(encPuestosSeleccionados).filter((id) => normPuestoId(id) !== null);

  }



  function encProgramaTienePlanesConCursos(programa) {
    const planes = programa?.planes || [];
    if (!planes.length && (programa?.planes_count || 0) > 0) return true;
    return planes.some((pl) => (pl.cursos && pl.cursos.length > 0) || (pl.cursos_count || 0) > 0);
  }

  function encProgramasByNombre(nombre) {
    const key = (nombre || "").trim().toLowerCase();
    if (!key) return [];
    return encProgramasFiltradosPorPuestos().filter((p) => (p.nombre || "").trim().toLowerCase() === key);
  }

  function encProgramasViables(items) {
    return (items || []).filter(encProgramaTienePlanesConCursos);
  }

  function encProgramaCubrePuestos(programa, puestoIds) {
    if (!puestoIds.length) return false;
    const pids = (programa.puestos || []).map((p) => normPuestoId(p.id)).filter((id) => id !== null);
    return puestoIds.every((id) => pids.includes(id));
  }

  function encProgramasFiltradosPorPuestos() {
    const ids = getEncPuestosSeleccionados();
    if (!ids.length) return [];
    return encProgramasViables(encProgramasCache).filter((p) => encProgramaCubrePuestos(p, ids));
  }

  function encNombresDisponibles() {
    const names = new Set();
    encProgramasFiltradosPorPuestos().forEach((p) => {
      if ((p.nombre || "").trim()) names.add(p.nombre.trim());
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b, "es"));
  }

  function encPuestosDisponibles() {
    const fromProg = new Set();
    (encProgramasCache || []).forEach((prog) => {
      (prog.puestos || []).forEach((p) => {
        const id = normPuestoId(p.id);
        if (id !== null) fromProg.add(id);
      });
    });
    return (metaPuestos || []).filter(
      (p) => p.en_uso || fromProg.has(normPuestoId(p.id)) || encPuestoSetHas(p.id)
    );
  }

  function encTiposDisponibles(nombre) {
    const tipos = new Set(
      encProgramasViables(encProgramasByNombre(nombre)).map((p) => p.tipo || "interno")
    );
    return Array.from(tipos);
  }

  function resolveEncPrograma(nombre, tipo) {
    const items = encProgramasViables(encProgramasByNombre(nombre)).filter(
      (p) => (p.tipo || "interno") === tipo
    );
    return items[0] || null;
  }

  function getEncProgramaActual() {
    const nombre = document.getElementById("cap-enc-programa")?.value || "";
    const tipo = document.getElementById("cap-enc-tipo")?.value || "";
    if (!nombre || !tipo) return null;
    return resolveEncPrograma(nombre, tipo);
  }

  async function ensureEncProgramaDetalle() {
    const programa = getEncProgramaActual();
    if (!programa?.id) return null;
    if (programa.puestos?.length) return programa;
    try {
      const data = await fetchJson(`${API}/programas/${programa.id}`);
      const detalle = data.programa;
      if (detalle) {
        encProgramasCache = encProgramasCache.map((p) =>
          (p.id === detalle.id ? { ...p, ...detalle } : p)
        );
        return detalle;
      }
    } catch (e) {
      console.error(e);
    }
    return programa;
  }

  function encPlanesDelPrograma(programa) {
    if (!programa) return [];
    const planes = programa.planes || [];
    return planes.filter((pl) => (pl.cursos && pl.cursos.length > 0) || (pl.cursos_count || 0) > 0);
  }

  async function loadEncProgramas() {
    const data = await fetchJson(`${API}/programas?detalle=1`);
    encProgramasCache = (data.programas || []).filter((p) => p.activo !== false);
    return encProgramasCache;
  }

  function fillEncProgramaSelect(selectedNombre = "") {
    const sel = document.getElementById("cap-enc-programa");
    if (!sel) return;
    const hayPuestos = getEncPuestosSeleccionados().length > 0;
    const nombres = encNombresDisponibles();
    const placeholder = !hayPuestos
      ? "— Seleccioná al menos un puesto —"
      : (nombres.length ? "— Seleccionar plan de carrera —" : "— Ningún plan de carrera aplica a esos puestos —");
    sel.innerHTML = `<option value="">${placeholder}</option>`;
    nombres.forEach((nombre) => {
      const opt = document.createElement("option");
      opt.value = nombre;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    sel.disabled = !hayPuestos || nombres.length === 0;
    if (selectedNombre && nombres.includes(selectedNombre)) {
      sel.value = selectedNombre;
    } else if (selectedNombre) {
      const opt = document.createElement("option");
      opt.value = selectedNombre;
      opt.textContent = selectedNombre;
      sel.appendChild(opt);
      sel.disabled = false;
      sel.value = selectedNombre;
    } else if (nombres.length === 1) {
      sel.value = nombres[0];
    }
  }

  function fillEncTipoSelect(nombre, selectedTipo = "") {
    const sel = document.getElementById("cap-enc-tipo");
    if (!sel) return;
    const tipos = encTiposDisponibles(nombre);
    sel.innerHTML = '<option value="">— Seleccionar tipo —</option>';
    if (tipos.includes("interno")) {
      sel.innerHTML += '<option value="interno">GOS Interno</option>';
    }
    if (tipos.includes("externo")) {
      sel.innerHTML += '<option value="externo">Externo</option>';
    }
    sel.disabled = !nombre || tipos.length === 0;
    if (selectedTipo && tipos.includes(selectedTipo)) {
      sel.value = selectedTipo;
    } else if (tipos.length === 1) {
      sel.value = tipos[0];
    }
  }

  function fillEncPlanSelect(selectedPlanId = "") {
    const sel = document.getElementById("cap-enc-plan");
    if (!sel) return;
    const programa = getEncProgramaActual();
    const planes = encPlanesDelPrograma(programa);
    sel.innerHTML = '<option value="">— Seleccionar plan —</option>';
    planes.forEach((pl) => {
      const opt = document.createElement("option");
      opt.value = pl.id;
      opt.textContent = pl.nombre;
      sel.appendChild(opt);
    });
    sel.disabled = !programa || planes.length === 0;
    if (selectedPlanId && planes.some((pl) => String(pl.id) === String(selectedPlanId))) {
      sel.value = String(selectedPlanId);
    } else if (planes.length === 1) {
      sel.value = String(planes[0].id);
    }
  }

  function resetEncCascadeFrom(level) {
    if (level === "puestos") {
      fillEncProgramaSelect();
      fillEncTipoSelect("");
      fillEncPlanSelect();
    } else if (level === "programa") {
      fillEncTipoSelect("");
      fillEncPlanSelect();
    } else if (level === "tipo") {
      fillEncPlanSelect();
    }
    if (level !== "plan") {
      const cursoSel = document.getElementById("cap-enc-curso");
      if (cursoSel) {
        cursoSel.disabled = true;
        cursoSel.innerHTML = '<option value="">— Seleccioná un plan primero —</option>';
      }
      document.getElementById("cap-enc-curso-meta")?.classList.add("cap-hidden");
    }
  }

  function onEncProgramaChange() {
    const nombre = document.getElementById("cap-enc-programa")?.value || "";
    fillEncTipoSelect(nombre);
    fillEncPlanSelect();
    const cursoSel = document.getElementById("cap-enc-curso");
    if (cursoSel) {
      cursoSel.disabled = true;
      cursoSel.innerHTML = '<option value="">— Seleccioná un plan primero —</option>';
    }
    document.getElementById("cap-enc-curso-meta")?.classList.add("cap-hidden");
    const tipo = document.getElementById("cap-enc-tipo")?.value || "";
    if (nombre && tipo) onEncTipoChange();
  }

  function onEncTipoChange() {
    const nombre = document.getElementById("cap-enc-programa")?.value || "";
    const tipo = document.getElementById("cap-enc-tipo")?.value || "";
    fillEncPlanSelect();
    const cursoSel = document.getElementById("cap-enc-curso");
    if (cursoSel) {
      cursoSel.disabled = true;
      cursoSel.innerHTML = '<option value="">— Seleccioná un plan primero —</option>';
    }
    document.getElementById("cap-enc-curso-meta")?.classList.add("cap-hidden");
    const origenSel = document.getElementById("cap-enc-origen");
    if (origenSel) origenSel.value = tipo === "externo" ? "externa" : "interna";
    if (nombre && tipo) {
      fillEncPlanSelect();
      if (document.getElementById("cap-enc-plan")?.value) onEncPlanChange().catch(console.error);
    }
  }

  async function onEncPlanChange() {
    await loadEncCursos();
  }

  function getEncPuestosDelPrograma() {
    return encPuestosDisponibles();
  }



  function renderEncPuestos() {

    const el = document.getElementById("cap-enc-puestos");

    if (!el) return;

    const items = encPuestosDisponibles();

    if (!items.length) {

      el.innerHTML = '<p class="cap-empty">No hay puestos vigentes. Asigná puestos a las personas en <strong>Personas</strong> y después definí el plan de carrera.</p>';

      return;

    }

    el.innerHTML = `

      ${items.map((p) => `

      <label class="cap-check-item">

        <input type="checkbox" value="${p.id}" data-enc-puesto ${encPuestoSetHas(p.id) ? "checked" : ""}>

        <span>${p.codigo} — ${p.nombre}</span>

      </label>`).join("")}`;

    el.querySelectorAll("[data-enc-puesto]").forEach((cb) => {

      cb.addEventListener("change", () => {

        const id = normPuestoId(cb.value);

        if (id === null) return;

        if (cb.checked) encPuestosSeleccionados.add(id);

        else encPuestosSeleccionados.delete(id);

        onEncPuestosChange().catch(console.error);

      });

    });

  }



  async function onEncPuestosChange() {
    const nombrePrev = document.getElementById("cap-enc-programa")?.value || "";
    const tipoPrev = document.getElementById("cap-enc-tipo")?.value || "";
    const planPrev = document.getElementById("cap-enc-plan")?.value || "";
    fillEncProgramaSelect(nombrePrev);
    const nombre = document.getElementById("cap-enc-programa")?.value || "";
    if (!nombre) {
      resetEncCascadeFrom("programa");
    } else {
      fillEncTipoSelect(nombre, tipoPrev);
      fillEncPlanSelect(planPrev);
      if (document.getElementById("cap-enc-plan")?.value) {
        await loadEncCursos();
      }
    }
    await loadEncPersonas();
  }



  async function loadEncPersonas(selectedIds = null, { todas = false } = {}) {

    const el = document.getElementById("cap-enc-personas");

    const countEl = document.getElementById("cap-enc-personas-count");

    if (!el) return;

    const puestoIds = getEncPuestosSeleccionados();

    if (!todas && !puestoIds.length) {

      encPersonasCache = [];

      el.innerHTML = '<p class="cap-empty">Seleccioná al menos un puesto en el paso 1</p>';

      if (countEl) countEl.textContent = "";

      return;

    }

    const programa = await ensureEncProgramaDetalle();

    el.innerHTML = '<p class="cap-loading">Cargando personas...</p>';

    const url = todas

      ? `${API}/participantes?`

      : programa?.id

        ? `${API}/programas/${programa.id}/participantes?puesto_ids=${puestoIds.join(",")}`

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

        <span>${escapeHtml(p.nombre)}${p.legajo ? ` <span class="cap-muted">(${escapeHtml(p.legajo)})</span>` : ""}${p.puesto_nombre ? ` <span class="cap-muted">— ${escapeHtml(p.puesto_nombre)}</span>` : ""}</span>

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
    const planId = document.getElementById("cap-enc-plan")?.value;
    if (!sel) return;
    if (!planId) {
      sel.disabled = true;
      sel.innerHTML = '<option value="">— Seleccioná un plan primero —</option>';
      document.getElementById("cap-enc-curso-meta")?.classList.add("cap-hidden");
      return;
    }
    sel.disabled = false;
    const programa = getEncProgramaActual();
    const planLocal = programa?.planes?.find((pl) => String(pl.id) === String(planId));
    let cursos = planLocal?.cursos || [];
    if (!cursos.length) {
      const data = await fetchJson(`${API}/planes/${planId}/cursos`);
      cursos = data.cursos || [];
    }
    fillSelect("cap-enc-curso", cursos.map((c) => ({ id: c.curso_id || c.id, codigo: c.curso_codigo || c.codigo, nombre: c.curso_nombre || c.nombre })), "— Seleccionar curso —");
    onEncCursoChange();
  }

  function showEncCursoMeta(curso) {
    const meta = document.getElementById("cap-enc-curso-meta");
    if (!meta) return;
    if (!curso) {
      meta.classList.add("cap-hidden");
      return;
    }
    const hs = curso.horas ?? curso.duracion_horas ?? "—";
    const ev = curso.requiere_evaluacion ? `Sí (mín. ${curso.puntaje_minimo ?? 0})` : "No";
    const vig = curso.tiene_vigencia
      ? `Sí (${curso.vigencia_meses} meses)`
      : "No";
    meta.innerHTML = `<strong>Duración:</strong> ${hs} hs · <strong>Evaluación:</strong> ${ev} · <strong>Vencimiento:</strong> ${vig}`;
    meta.classList.remove("cap-hidden");
  }

  function onEncCursoChange() {
    const cursoId = document.getElementById("cap-enc-curso")?.value;
    const planId = document.getElementById("cap-enc-plan")?.value;
    if (!cursoId || !planId) return;
    const programa = getEncProgramaActual();
    const planLocal = programa?.planes?.find((pl) => String(pl.id) === String(planId));
    const c = (planLocal?.cursos || []).find((x) => String(x.curso_id || x.id) === String(cursoId));
    if (c) {
      showEncCursoMeta(c || null);
      updateEncFechaFin();
      return;
    }
    fetchJson(`${API}/planes/${planId}/cursos`).then((data) => {
      const found = (data.cursos || []).find((x) => String(x.curso_id || x.id) === String(cursoId));
      showEncCursoMeta(found || null);
      updateEncFechaFin();
    }).catch(console.error);
  }

  function toDatetimeLocalValue(d) {
    if (!d) return "";
    const dt = d instanceof Date ? d : new Date(d);
    if (Number.isNaN(dt.getTime())) return "";
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}T${String(dt.getHours()).padStart(2, "0")}:${String(dt.getMinutes()).padStart(2, "0")}`;
  }

  function siguienteHabilJs(dt) {
    const d = new Date(dt);
    while (d.getDay() === 0 || d.getDay() === 6) {
      d.setDate(d.getDate() + 1);
    }
    d.setHours(9, 0, 0, 0);
    return d;
  }

  function calcularFechaFinJs(fechaStr, horaInicio, duracionHoras) {
    if (!fechaStr || !duracionHoras || duracionHoras <= 0) return null;
    const [y, m, d] = fechaStr.split("-").map(Number);
    const [hh, mm] = (horaInicio || "09:00").slice(0, 5).split(":").map(Number);
    let actual = new Date(y, m - 1, d, hh || 9, mm || 0);
    let restante = Number(duracionHoras);

    if (restante <= 8) {
      return new Date(actual.getTime() + restante * 3600000);
    }

    while (restante > 0) {
      if (actual.getDay() === 0 || actual.getDay() === 6) {
        actual = siguienteHabilJs(actual);
        continue;
      }
      const bloque = Math.min(restante, 8);
      actual = new Date(actual.getTime() + bloque * 3600000);
      restante -= bloque;
      if (restante > 0) {
        const next = new Date(actual);
        next.setDate(next.getDate() + 1);
        next.setHours(9, 0, 0, 0);
        actual = siguienteHabilJs(next);
      }
    }
    return actual;
  }

  function updateEncFechaFin() {
    const cursoId = document.getElementById("cap-enc-curso")?.value;
    const fecha = document.getElementById("cap-enc-fecha")?.value;
    const horaInicio = document.getElementById("cap-enc-hora-inicio")?.value || "09:00";
    const finEl = document.getElementById("cap-enc-fecha-fin");
    if (!finEl || !cursoId) {
      if (finEl) finEl.value = "";
      return;
    }
    // Planificación por mes: el campo es YYYY-MM, no se calcula fecha fin exacta.
    if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha || "")) {
      finEl.value = "";
      return;
    }
    const planId = document.getElementById("cap-enc-plan")?.value;
    if (!planId) return;
    fetchJson(`${API}/planes/${planId}/cursos`).then((data) => {
      const c = (data.cursos || []).find((x) => String(x.curso_id || x.id) === String(cursoId));
      const horas = parseFloat(c?.horas ?? c?.duracion_horas ?? 0);
      if (!fecha || !horas) return;
      const end = calcularFechaFinJs(fecha, horaInicio, horas);
      if (end && !finEl.dataset.userEdited) finEl.value = toDatetimeLocalValue(end);
    }).catch(console.error);
  }



  async function loadEncCatalogos() {

    await ensureTaxonomia();

    fillCascadeSelect("cap-enc-origen", taxListaEntries("origenes"), "— Seleccionar origen —", false);

    const [instData] = await Promise.all([

      fetchJson(`${API}/instructores`),

    ]);

    const instructores = (instData.instructores || []).map((i) => ({ id: i.id, nombre: i.nombre }));

    fillSelect("cap-enc-instructor", instructores, "— Seleccionar capacitador —");

    fillSelect("cap-bpc-instructor", instructores, "— Seleccionar capacitador —");

  }



  function isEncBpcMode() {
    return Boolean(document.getElementById("cap-enc-bpc-check")?.checked);
  }

  function setEncRequiredAttrs(enabled) {
    ["cap-enc-programa", "cap-enc-tipo", "cap-enc-plan", "cap-enc-curso"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (enabled) el.setAttribute("required", "");
      else el.removeAttribute("required");
    });
  }

  function updateBpcFileList() {
    const input = document.getElementById("cap-bpc-archivos");
    const list = document.getElementById("cap-bpc-file-list");
    if (!list) return;
    const files = input?.files ? Array.from(input.files) : [];
    list.innerHTML = files.length
      ? files.map((f) => `<li>${escapeHtml(f.name)} <span class="cap-muted">(${Math.round(f.size / 1024)} KB)</span></li>`).join("")
      : "";
  }

  function updateBpcPersonasCount() {
    const n = document.querySelectorAll("#cap-bpc-personas [data-bpc-persona]:checked").length;
    const el = document.getElementById("cap-bpc-personas-count");
    if (el) el.textContent = n ? `${n} seleccionada${n === 1 ? "" : "s"}` : "0 personas";
  }

  function getBpcPersonasSeleccionadas() {
    return Array.from(document.querySelectorAll("#cap-bpc-personas [data-bpc-persona]:checked")).map((cb) => Number(cb.value));
  }

  async function loadBpcPersonas(selectedIds = null) {
    const el = document.getElementById("cap-bpc-personas");
    if (!el) return;
    el.innerHTML = '<p class="cap-loading">Cargando personas...</p>';
    const data = await fetchJson(`${API}/participantes?`);
    const personas = data.participantes || [];
    if (!personas.length) {
      el.innerHTML = '<p class="cap-empty">No hay personas activas</p>';
      updateBpcPersonasCount();
      return;
    }
    const selected = selectedIds instanceof Set ? selectedIds : null;
    el.innerHTML = personas.map((p) => `
      <label class="cap-check-item">
        <input type="checkbox" value="${p.id}" data-bpc-persona ${selected ? (selected.has(p.id) ? "checked" : "") : ""}>
        <span>${escapeHtml(p.nombre_completo || p.nombre || "")}${p.puesto_nombre ? ` <span class="cap-muted">· ${escapeHtml(p.puesto_nombre)}</span>` : ""}</span>
      </label>`).join("");
    el.querySelectorAll("[data-bpc-persona]").forEach((cb) => {
      cb.addEventListener("change", updateBpcPersonasCount);
    });
    updateBpcPersonasCount();
  }

  async function setEncBpcMode(on) {
    const check = document.getElementById("cap-enc-bpc-check");
    if (check) check.checked = Boolean(on);
    const prog = document.getElementById("cap-enc-modo-programa");
    const bpc = document.getElementById("cap-enc-modo-bpc");
    prog?.classList.toggle("cap-hidden", Boolean(on));
    bpc?.classList.toggle("cap-hidden", !on);
    setEncRequiredAttrs(!on);
    updateEncuentroFormMode(Boolean(encuentroEditId));
    if (on) {
      const hoy = new Date();
      const fechaEl = document.getElementById("cap-bpc-fecha");
      if (fechaEl && !fechaEl.value) {
        fechaEl.value = `${hoy.getFullYear()}-${pad(hoy.getMonth() + 1)}-${pad(hoy.getDate())}`;
      }
      const bpcInst = document.getElementById("cap-bpc-instructor");
      const encInst = document.getElementById("cap-enc-instructor");
      if (bpcInst && encInst && bpcInst.options.length <= 1) {
        bpcInst.innerHTML = encInst.innerHTML;
      }
      await loadBpcPersonas();
    }
  }

  function updateEncuentroFormMode(editing) {
    const hint = document.getElementById("cap-encuentro-form-hint");
    const submit = document.getElementById("cap-encuentro-submit");
    const delBtn = document.getElementById("cap-encuentro-eliminar");
    const bpc = isEncBpcMode();

    if (hint) {
      if (bpc) {
        hint.textContent = "Buenas Prácticas Compartidas — Charla con acreditación en la matriz analítica.";
      } else {
        hint.textContent = editing
          ? "Etapa A — Modificá la planificación. Puesto → Plan de carrera → Tipo → Plan → Personas."
          : "Etapa A — Puesto → Plan de carrera → Tipo → Plan → Personas. Cada paso habilita el siguiente.";
      }
    }

    if (submit) {
      if (bpc) submit.textContent = "Registrar charla";
      else submit.textContent = editing ? "Guardar cambios" : "Guardar cronograma";
    }

    if (delBtn) delBtn.classList.toggle("cap-hidden", !editing || bpc);
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
    updateEncFechaFin();
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
    togglePanel("cap-enc-instructor-quick", false);
    togglePanel("cap-bpc-instructor-quick", false);
  }



  async function resetEncuentroForm() {

    const form = document.getElementById("cap-encuentro-form");

    if (form) form.reset();

    encuentroEditId = null;

    encPuestosSeleccionados = new Set();

    setFormError("cap-encuentro-form-error", "");

    closeEncQuickForms();
    togglePanel("cap-bpc-instructor-quick", false);
    const fileList = document.getElementById("cap-bpc-file-list");
    if (fileList) fileList.innerHTML = "";

    await setEncBpcMode(false);

    updateEncuentroFormMode(false);

    await loadEncProgramas();
    renderEncPuestos();
    fillEncProgramaSelect();
    resetEncCascadeFrom("programa");
    await loadEncPersonas();

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
    document.getElementById("cap-enc-bpc-check")?.removeAttribute("disabled");
    document.getElementById("cap-encuentro-submit")?.classList.remove("cap-hidden");

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

    if (data.es_buenas_practicas) {
      await setEncBpcMode(true);
      const check = document.getElementById("cap-enc-bpc-check");
      if (check) check.disabled = true;
      document.getElementById("cap-bpc-nombre").value = data.curso_nombre || data.titulo || "";
      document.getElementById("cap-bpc-fecha").value = data.fecha_realizacion || data.fecha || "";
      setEncFormVal("cap-bpc-instructor", data.instructor_id || "");
      setEncFormVal("cap-bpc-lugar", data.lugar || "");
      const selected = new Set((data.participantes || []).map((p) => p.participante_id));
      await loadBpcPersonas(selected);
      const submit = document.getElementById("cap-encuentro-submit");
      if (submit) submit.classList.add("cap-hidden");
      const hint = document.getElementById("cap-encuentro-form-hint");
      if (hint) hint.textContent = "Charla ya registrada. Podés eliminarla y cargarla de nuevo si necesitás corregirla.";
      const delBtn = document.getElementById("cap-encuentro-eliminar");
      if (delBtn) delBtn.classList.remove("cap-hidden");
      togglePanel("cap-encuentro-form-panel", true);
      return;
    }

    document.getElementById("cap-enc-bpc-check")?.removeAttribute("disabled");
    document.getElementById("cap-encuentro-submit")?.classList.remove("cap-hidden");
    await setEncBpcMode(false);
    await loadEncProgramas();

    let programa = encProgramasCache.find((p) => p.id === data.programa_id);
    if (!programa && data.programa_id) {
      try {
        const pd = await fetchJson(`${API}/programas/${data.programa_id}`);
        programa = pd.programa;
        if (programa) encProgramasCache = encProgramasCache.map((p) => (p.id === programa.id ? { ...p, ...programa } : p));
        if (programa && !encProgramasCache.some((p) => p.id === programa.id)) encProgramasCache.push(programa);
      } catch (e) {
        console.error(e);
      }
    }

    const participantes = data.participantes || [];

    const participanteIds = new Set(participantes.map((p) => p.participante_id));

    encPuestosSeleccionados = new Set(

      participantes.map((p) => normPuestoId(p.puesto_id)).filter((id) => id !== null)

    );

    if (programa) {
      const tipo = programa.tipo || data.tipo || "interno";
      renderEncPuestos();
      fillEncProgramaSelect(programa.nombre);
      document.getElementById("cap-enc-programa").value = programa.nombre;
      fillEncTipoSelect(programa.nombre, tipo);
      fillEncPlanSelect(data.plan_id);
      await onEncPlanChange();
      renderEncPuestos();
      await loadEncPersonas(participanteIds);
    } else if (data.programa_nombre) {
      const tipo = data.programa_tipo || data.tipo || "interno";
      renderEncPuestos();
      fillEncProgramaSelect(data.programa_nombre);
      document.getElementById("cap-enc-programa").value = data.programa_nombre;
      fillEncTipoSelect(data.programa_nombre, tipo);
      fillEncPlanSelect(data.plan_id);
      await onEncPlanChange();
      renderEncPuestos();
      await loadEncPersonas(participanteIds);
    } else {
      renderEncPuestos();
      await loadEncPersonas(participanteIds);
    }

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

    setEncFormVal("cap-enc-fecha", data.mes || (data.fecha ? String(data.fecha).slice(0, 7) : ""));

    setEncFormVal("cap-enc-hora-inicio", formatTimeInput(data.hora_inicio));

    setEncFormVal("cap-enc-hora-fin", formatTimeInput(data.hora_fin));

    setEncFormVal("cap-enc-origen", data.origen || "");

    setEncFormVal("cap-enc-instructor", data.instructor_id || "");

    setEncFormVal("cap-enc-lugar", data.lugar || "");

    setEncFormVal("cap-enc-link", data.link_virtual || "");

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

    await loadEncuentros(true);

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

      const mes = ev.mes || (ev.fecha ? String(ev.fecha).slice(0, 7) : "");

      let txt = "";

      if (mes) {

        const [yy, mm] = mes.split("-");

        txt = `Programado: ${MESES[Number(mm) - 1] || ""} ${yy}`;

      }

      if (ev.fecha_realizacion) {

        const p = String(ev.fecha_realizacion).split("-");

        if (p.length === 3) txt += `${txt ? " · " : ""}Realizado el ${p[2]}/${p[1]}/${p[0]}`;

      }

      fechaEl.textContent = txt;

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

    document.getElementById("cap-enc-programa")?.addEventListener("change", () => onEncProgramaChange());
    document.getElementById("cap-enc-tipo")?.addEventListener("change", () => onEncTipoChange());
    document.getElementById("cap-enc-plan")?.addEventListener("change", () => onEncPlanChange().catch(console.error));
    document.getElementById("cap-enc-curso")?.addEventListener("change", onEncCursoChange);
    document.getElementById("cap-enc-fecha")?.addEventListener("change", updateEncFechaFin);
    document.getElementById("cap-enc-hora-inicio")?.addEventListener("change", updateEncFechaFin);
    document.getElementById("cap-enc-hora-inicio")?.addEventListener("input", updateEncFechaFin);
    document.getElementById("cap-enc-fecha-fin")?.addEventListener("input", (e) => {
      e.target.dataset.userEdited = "1";
    });

    document.getElementById("cap-enc-instructor-add")?.addEventListener("click", () => {
      togglePanel("cap-enc-instructor-quick", true);
      document.getElementById("cap-enc-instructor-quick-nombre")?.focus();
    });

    document.getElementById("cap-enc-instructor-quick-cancel")?.addEventListener("click", () => togglePanel("cap-enc-instructor-quick", false));

    document.getElementById("cap-enc-instructor-quick-save")?.addEventListener("click", async () => {

      const nombre = document.getElementById("cap-enc-instructor-quick-nombre")?.value.trim();

      if (!nombre) {

        setFormError("cap-encuentro-form-error", "Indicá el nombre del capacitador");

        return;

      }

      try {

        const resolution = await resolveSimilarBeforeCreate({ tipo: "instructor", nombre });

        if (resolution.action === "cancel") return;

        if (resolution.action === "use") {

          appendEncSelectOption("cap-enc-instructor", resolution.item);

          document.getElementById("cap-enc-instructor-quick-nombre").value = "";

          togglePanel("cap-enc-instructor-quick", false);

          setFormError("cap-encuentro-form-error", "");

          return;

        }

        const data = await postJson(`${API}/instructores`, { nombre });

        appendEncSelectOption("cap-enc-instructor", data.instructor);

        document.getElementById("cap-enc-instructor-quick-nombre").value = "";

        togglePanel("cap-enc-instructor-quick", false);

        setFormError("cap-encuentro-form-error", "");

      } catch (err) {

        setFormError("cap-encuentro-form-error", err.message);

      }

    });

    document.getElementById("cap-enc-bpc-check")?.addEventListener("change", (e) => {
      setEncBpcMode(e.target.checked).catch(console.error);
    });

    document.getElementById("cap-bpc-sel-todos")?.addEventListener("click", () => {
      document.querySelectorAll("#cap-bpc-personas [data-bpc-persona]").forEach((cb) => { cb.checked = true; });
      updateBpcPersonasCount();
    });

    document.getElementById("cap-bpc-sel-ninguno")?.addEventListener("click", () => {
      document.querySelectorAll("#cap-bpc-personas [data-bpc-persona]").forEach((cb) => { cb.checked = false; });
      updateBpcPersonasCount();
    });

    document.getElementById("cap-bpc-archivos")?.addEventListener("change", updateBpcFileList);

    document.getElementById("cap-bpc-instructor-add")?.addEventListener("click", () => {
      togglePanel("cap-bpc-instructor-quick", true);
      document.getElementById("cap-bpc-instructor-quick-nombre")?.focus();
    });

    document.getElementById("cap-bpc-instructor-quick-cancel")?.addEventListener("click", () => {
      togglePanel("cap-bpc-instructor-quick", false);
    });

    document.getElementById("cap-bpc-instructor-quick-save")?.addEventListener("click", async () => {
      const nombre = document.getElementById("cap-bpc-instructor-quick-nombre")?.value.trim();
      if (!nombre) {
        setFormError("cap-encuentro-form-error", "Indicá el nombre del capacitador");
        return;
      }
      try {
        const resolution = await resolveSimilarBeforeCreate({ tipo: "instructor", nombre });
        if (resolution.action === "cancel") return;
        if (resolution.action === "use") {
          appendEncSelectOption("cap-bpc-instructor", resolution.item);
          appendEncSelectOption("cap-enc-instructor", resolution.item);
          document.getElementById("cap-bpc-instructor-quick-nombre").value = "";
          togglePanel("cap-bpc-instructor-quick", false);
          setFormError("cap-encuentro-form-error", "");
          return;
        }
        const data = await postJson(`${API}/instructores`, { nombre });
        appendEncSelectOption("cap-bpc-instructor", data.instructor);
        appendEncSelectOption("cap-enc-instructor", data.instructor);
        document.getElementById("cap-bpc-instructor-quick-nombre").value = "";
        togglePanel("cap-bpc-instructor-quick", false);
        setFormError("cap-encuentro-form-error", "");
      } catch (err) {
        setFormError("cap-encuentro-form-error", err.message);
      }
    });

    document.getElementById("cap-encuentro-form")?.addEventListener("submit", async (e) => {

      e.preventDefault();

      setFormError("cap-encuentro-form-error", "");

      if (isEncBpcMode()) {
        const participanteIds = getBpcPersonasSeleccionadas();
        const nombreCurso = document.getElementById("cap-bpc-nombre")?.value.trim();
        const fecha = document.getElementById("cap-bpc-fecha")?.value;
        if (!participanteIds.length) {
          setFormError("cap-encuentro-form-error", "Seleccioná al menos una persona");
          return;
        }
        if (!nombreCurso) {
          setFormError("cap-encuentro-form-error", "Indicá el nombre del curso / charla");
          return;
        }
        if (!fecha) {
          setFormError("cap-encuentro-form-error", "Indicá la fecha");
          return;
        }
        const body = {
          nombre_curso: nombreCurso,
          fecha,
          participante_ids: participanteIds,
          instructor_id: document.getElementById("cap-bpc-instructor")?.value || null,
          lugar: document.getElementById("cap-bpc-lugar")?.value || null,
        };
        try {
          const data = await postJson(`${API}/encuentros/buenas-practicas`, body);
          const encuentroId = data.encuentro?.id;
          const files = document.getElementById("cap-bpc-archivos")?.files;
          if (encuentroId && files?.length) {
            for (const file of Array.from(files)) {
              await uploadFile(`${API}/encuentros/${encuentroId}/adjuntos`, file);
            }
          }
          togglePanel("cap-encuentro-form-panel", false);
          encuentroEditId = null;
          await resetEncuentroForm();
          await loadEncuentros(true);
        } catch (err) {
          setFormError("cap-encuentro-form-error", err.message);
        }
        return;
      }

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

      const programa = getEncProgramaActual();
      if (!programa) {
        setFormError("cap-encuentro-form-error", "Completá plan de carrera y tipo");
        return;
      }
      body.programa_id = programa.id;
      body.tipo = document.getElementById("cap-enc-tipo")?.value || programa.tipo || "interno";
      delete body.empresa_capacitadora_id;

      if (!body.curso_id) {

        setFormError("cap-encuentro-form-error", "Seleccioná un curso");

        return;

      }

      if (!body.plan_id) {
        setFormError("cap-encuentro-form-error", "Seleccioná un plan");
        return;
      }

      body.puesto_ids = getEncPuestosSeleccionados();
      // Planificación por mes: el input es YYYY-MM; se guarda el día 1 del mes.
      const mesVal = document.getElementById("cap-enc-fecha")?.value;
      if (mesVal) {
        body.fecha = `${mesVal}-01`;
        body.fecha_inicio = `${mesVal}-01T09:00`;
      } else {
        delete body.fecha;
        delete body.fecha_inicio;
      }
      delete body.fecha_fin;

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

        await loadEncuentros(true);

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

      if (item.centro_id) document.getElementById("cap-p-centro").value = item.centro_id;

      if (item.sector_id) document.getElementById("cap-p-sector").value = item.sector_id;

      if (item.puesto_id) document.getElementById("cap-p-puesto").value = item.puesto_id;
      renderClienteChecks(item.cliente_ids || []);
    } else {
      renderClienteChecks([]);
    }

    document.getElementById("cap-persona-baja")?.classList.toggle("cap-hidden", !personaEditId);

    setFormError("cap-persona-form-error", "");

    togglePanel("cap-sector-quick", false);

    togglePanel("cap-puesto-quick", false);

    togglePanel("cap-centro-quick", false);

    togglePanel("cap-persona-form-panel", true);

    document.getElementById("cap-p-nombre")?.focus();

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

      togglePanel("cap-centro-quick", false);

      togglePanel("cap-sector-quick", true);

    });

    document.getElementById("cap-p-puesto-add")?.addEventListener("click", () => {

      togglePanel("cap-sector-quick", false);

      togglePanel("cap-centro-quick", false);

      togglePanel("cap-puesto-quick", true);

    });

    document.getElementById("cap-p-centro-add")?.addEventListener("click", () => {

      togglePanel("cap-sector-quick", false);

      togglePanel("cap-puesto-quick", false);

      togglePanel("cap-centro-quick", true);

    });

    document.getElementById("cap-sector-quick-cancel")?.addEventListener("click", () => togglePanel("cap-sector-quick", false));

    document.getElementById("cap-puesto-quick-cancel")?.addEventListener("click", () => togglePanel("cap-puesto-quick", false));

    document.getElementById("cap-centro-quick-cancel")?.addEventListener("click", () => togglePanel("cap-centro-quick", false));



    document.getElementById("cap-sector-quick-save")?.addEventListener("click", async () => {

      const codigo = document.getElementById("cap-sector-quick-codigo")?.value.trim();

      const nombre = document.getElementById("cap-sector-quick-nombre")?.value.trim();

      if (!codigo || !nombre) {

        setFormError("cap-persona-form-error", "Código y nombre del sector son obligatorios.");

        return;

      }

      try {

        const resolution = await resolveSimilarBeforeCreate({ tipo: "sector", nombre, codigo });

        if (resolution.action === "cancel") return;

        if (resolution.action === "use") {

          await loadMeta();

          document.getElementById("cap-p-sector").value = resolution.item.id;

          togglePanel("cap-sector-quick", false);

          setFormError("cap-persona-form-error", "");

          return;

        }

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

        const resolution = await resolveSimilarBeforeCreate({ tipo: "puesto", nombre, codigo });

        if (resolution.action === "cancel") return;

        if (resolution.action === "use") {

          await loadMeta();

          document.getElementById("cap-p-puesto").value = resolution.item.id;

          togglePanel("cap-puesto-quick", false);

          setFormError("cap-persona-form-error", "");

          return;

        }

        const data = await postJson(`${API}/puestos`, { codigo, nombre });

        await loadMeta();

        document.getElementById("cap-p-puesto").value = data.puesto.id;

        togglePanel("cap-puesto-quick", false);

        setFormError("cap-persona-form-error", "");

      } catch (err) {

        setFormError("cap-persona-form-error", err.message);

      }

    });



    document.getElementById("cap-centro-quick-save")?.addEventListener("click", async () => {

      const codigo = document.getElementById("cap-centro-quick-codigo")?.value.trim();

      const nombre = document.getElementById("cap-centro-quick-nombre")?.value.trim();

      if (!codigo || !nombre) {

        setFormError("cap-persona-form-error", "Código y nombre del centro son obligatorios.");

        return;

      }

      try {

        const resolution = await resolveSimilarBeforeCreate({ tipo: "centro", nombre, codigo });

        if (resolution.action === "cancel") return;

        if (resolution.action === "use") {

          await loadMeta();

          document.getElementById("cap-p-centro").value = resolution.item.id;

          togglePanel("cap-centro-quick", false);

          setFormError("cap-persona-form-error", "");

          return;

        }

        const data = await postJson(`${API}/centros`, { codigo, nombre });

        await loadMeta();

        document.getElementById("cap-p-centro").value = data.centro.id;

        togglePanel("cap-centro-quick", false);

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

      if (payload.centro_id) payload.centro_id = Number(payload.centro_id);
      payload.cliente_ids = selectedClienteIds();

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



  async function loadLegajoCarrera(p) {
    const wrap = document.getElementById("cap-legajo-carrera");
    if (!wrap) return;
    if (!p.puesto_id) {
      wrap.innerHTML = `<h3>Plan de carrera del puesto</h3>
        <p class="cap-empty">Esta persona no tiene puesto. Asignalo para ver el plan de carrera y hacer el seguimiento.</p>`;
      return;
    }
    try {
      const data = await fetchJson(`${API}/programas?puesto_id=${p.puesto_id}&detalle=1`);
      const programas = data.programas || [];
      if (!programas.length) {
        wrap.innerHTML = `<h3>Plan de carrera del puesto</h3>
          <p class="cap-muted">${escapeHtml(p.puesto_nombre || "Puesto")}</p>
          <p class="cap-empty">Este puesto todavía no tiene plan de carrera. Cargalo en <strong>Planes de carrera</strong>.</p>`;
        return;
      }
      wrap.innerHTML = `<h3>Plan de carrera del puesto</h3>
        <p class="cap-muted">${escapeHtml(p.puesto_nombre || "Puesto")} → plan de carrera → planes</p>
        ${programas.map((prog) => {
          const tipo = prog.tipo === "externo" ? "Externo" : "Interno";
          const planes = (prog.planes || []).map((pl) => {
            const cursos = (pl.cursos || []).map((c) => escapeHtml(c.curso_nombre || "")).filter(Boolean);
            return `<li><strong>${escapeHtml(pl.nombre)}</strong>${cursos.length ? ` · ${cursos.join(", ")}` : ""}</li>`;
          }).join("") || "<li class=\"cap-muted\">Sin planes</li>";
          return `<section class="cap-plan-block">
            <div class="cap-plan-head"><h4>${escapeHtml(prog.nombre)}</h4><span class="cap-badge ${prog.tipo === "externo" ? "cap-badge--yellow" : "cap-badge--blue"}">${tipo}</span></div>
            <ul class="cap-plan-cursos">${planes}</ul>
          </section>`;
        }).join("")}`;
    } catch (err) {
      wrap.innerHTML = `<h3>Plan de carrera del puesto</h3><p class="cap-empty">${escapeHtml(err.message || "No se pudieron cargar los planes de carrera")}</p>`;
    }
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
          ${renderLegajoCampo("Email", p.email)}
          ${renderLegajoCampo("Sector", p.sector_nombre)}
          ${renderLegajoCampo("Puesto", p.puesto_nombre)}
          ${renderLegajoCampo("Centro", p.centro_nombre)}
          ${renderLegajoCampo("Clientes", nombresClientes(p.cliente_ids))}
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


  function personaCell(value) {
    const text = String(value ?? "").trim();
    return text ? escapeHtml(text) : "—";
  }

  function personaRowEl(id) {
    return document.querySelector(`#cap-personas-body tr[data-id="${id}"]`);
  }

  function collapsePersonaDetail() {
    document.querySelectorAll("#cap-personas-body tr.cap-row-active").forEach((el) => {
      el.classList.remove("cap-row-active");
    });
    document.getElementById("cap-persona-detail-row")?.remove();
  }

  function mountPersonaDetailAfter(row) {
    let detailTr = document.getElementById("cap-persona-detail-row");
    if (!detailTr) {
      detailTr = document.createElement("tr");
      detailTr.id = "cap-persona-detail-row";
      detailTr.innerHTML = '<td colspan="8"><div id="cap-persona-detail-active" class="cap-persona-detail"></div></td>';
    }
    if (detailTr.previousElementSibling !== row) {
      detailTr.remove();
      row.insertAdjacentElement("afterend", detailTr);
    }
    return document.getElementById("cap-persona-detail-active");
  }

  function isPersonaExpanded(id) {
    if (String(personaSeleccionadaId) !== String(id)) return false;
    const detailTr = document.getElementById("cap-persona-detail-row");
    const row = personaRowEl(id);
    return Boolean(detailTr && row && detailTr.previousElementSibling === row);
  }

  async function loadPersonas(selectId) {
    const tbody = document.getElementById("cap-personas-body");
    if (!tbody) return;

    collapsePersonaDetail();
    tbody.innerHTML = '<tr><td colspan="8" class="cap-loading">Cargando...</td></tr>';

    const q = document.getElementById("cap-personas-q")?.value?.trim() || "";
    const sectorId = document.getElementById("cap-personas-sector")?.value || "";
    let url = `${API}/participantes?`;
    if (q) url += `q=${encodeURIComponent(q)}&`;
    if (sectorId) url += `sector_id=${sectorId}&`;

    const items = (await fetchJson(url)).participantes || [];
    personasCache = items;

    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="cap-empty">Sin participantes cargados</td></tr>';
      personaSeleccionadaId = null;
      return;
    }

    tbody.innerHTML = items.map((p) => `
      <tr data-id="${p.id}">
        <td>
          <div class="cap-persona-nombre-cell">
            <span class="cap-persona-card__avatar">${renderPersonaAvatar(p)}</span>
            <button type="button" class="cap-persona-nombre-btn" data-persona-open="${p.id}">${personaCell(p.nombre)}</button>
          </div>
        </td>
        <td>${personaCell(p.legajo)}</td>
        <td>${personaCell(p.email)}</td>
        <td>${personaCell(p.centro_nombre)}</td>
        <td>${personaCell(p.sector_nombre)}</td>
        <td>${personaCell(p.puesto_nombre)}</td>
        <td>${personaCell(nombresClientes(p.cliente_ids))}</td>
        <td class="cap-col-actions">${editButton("Editar persona", { id: p.id })}</td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-persona-open]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.personaOpen;
        if (personaSeleccionadaId === id && isPersonaExpanded(id)) {
          deselectPersona();
          return;
        }
        selectPersona(id, personaRowEl(id));
      });
    });

    tbody.querySelectorAll(".cap-btn-edit").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const item = personasCache.find((x) => String(x.id) === String(btn.dataset.id));
        if (!item) return;
        await loadMeta();
        openPersonaForm({
          id: item.id,
          nombre: item.nombre,
          legajo: item.legajo,
          email: item.email,
          centro_id: item.centro_id,
          sector_id: item.sector_id,
          puesto_id: item.puesto_id,
          cliente_ids: item.cliente_ids || [],
        });
        document.getElementById("cap-persona-form-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });

    if (selectId) {
      const target = personaRowEl(selectId);
      if (target) {
        target.classList.add("cap-row-active");
        target.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }

  function deselectPersona() {
    personaSeleccionadaId = null;
    collapsePersonaDetail();
  }

  async function selectPersona(id, btn) {
    const row = btn?.tagName === "TR" ? btn : personaRowEl(id);
    if (!row) return;

    collapsePersonaDetail();
    row.classList.add("cap-row-active");
    personaSeleccionadaId = id;
    const detail = mountPersonaDetailAfter(row);

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
      <div class="cap-legajo-carrera" id="cap-legajo-carrera">
        <h3>Plan de carrera del puesto</h3>
        <p class="cap-loading">Cargando planes de carrera...</p>
      </div>

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



    loadLegajoCarrera(p).catch(console.error);

    document.getElementById("cap-btn-editar-persona")?.addEventListener("click", async () => {

      await loadMeta();

      openPersonaForm({

        id: p.id,

        nombre: nombreDisplay,

        legajo: p.legajo,

        email: p.email,

        centro_id: p.centro_id,

        sector_id: p.sector_id,

        puesto_id: p.puesto_id,
        cliente_ids: p.cliente_ids || [],
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
        await loadPersonas(id);
        await selectPersona(id);

      } catch (e) {

        alert(e.message);

      }

    });

    btn.scrollIntoView({ behavior: "smooth", block: "nearest" });

  }



  function bindFotoUpload() {

    document.getElementById("cap-foto-upload-file")?.addEventListener("change", async (ev) => {

      const file = ev.target.files?.[0];

      ev.target.value = "";

      if (!file || !personaSeleccionadaId) return;

      try {

        await uploadFile(`${API}/participantes/${personaSeleccionadaId}/foto`, file);
        const id = personaSeleccionadaId;
        await loadPersonas(id);
        await selectPersona(id);

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

    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="cap-loading">Cargando...</td></tr>';

    const items = (await fetchJson(`${API}/cursos`)).cursos || [];

    window.capCursosCache = items;

    if (document.getElementById("cap-req-curso")) refreshProgramaCursoSelect();

    if (!tbody) return;

    if (!items.length) {

      tbody.innerHTML = '<tr><td colspan="6" class="cap-empty">Sin cursos cargados</td></tr>';

      return;

    }

    tbody.innerHTML = items

      .map(

        (c) => `<tr>

        <td><strong>${c.codigo}</strong></td>

        <td>${c.nombre}</td>

        <td>${cursoClasificacionLabel(c, "tipo")}</td>

        <td>${cursoClasificacionLabel(c, "modalidad")}</td>

        <td>${c.horas != null ? c.horas : "—"}</td>

        <td class="cap-col-actions">${editButton("Editar", { id: c.id })}</td>

      </tr>`

      )

      .join("");

    bindCatalogTableEdits("cap-cursos-body", (ds) => openCursoForm(items.find((x) => String(x.id) === String(ds.id))));

  }



  function syncCursoEvalFields() {
    const evalChk = document.getElementById("cap-c-eval");
    const puntWrap = document.getElementById("cap-c-puntaje-wrap");
    if (evalChk && puntWrap) {
      puntWrap.classList.toggle("cap-hidden", !evalChk.checked);
    }
  }



  function syncCursoVigenciaFields() {
    const chk = document.getElementById("cap-c-vigencia-chk");
    const wrap = document.getElementById("cap-c-vigencia-wrap");
    if (chk && wrap) {
      wrap.classList.toggle("cap-hidden", !chk.checked);
    }
    if (!chk?.checked) {
      const hidden = document.getElementById("cap-c-vigencia");
      const sel = document.getElementById("cap-c-vigencia-periodo");
      if (hidden) hidden.value = "";
      if (sel) sel.value = "";
    }
  }



  async function ensurePeriodosVigencia() {
    if (periodosVigenciaCache) return periodosVigenciaCache;
    const data = await fetchJson(`${API}/periodos-vigencia`);
    periodosVigenciaCache = data.periodos || [];
    return periodosVigenciaCache;
  }



  function fillPeriodosVigenciaSelect(periodos, selectedMeses) {
    const sel = document.getElementById("cap-c-vigencia-periodo");
    if (!sel) return;
    sel.innerHTML = '<option value="">— Seleccionar período —</option>';
    periodos.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = String(p.meses);
      opt.textContent = p.label || `${p.meses} meses`;
      sel.appendChild(opt);
    });
    if (selectedMeses) {
      sel.value = String(selectedMeses);
      const hidden = document.getElementById("cap-c-vigencia");
      if (hidden) hidden.value = String(selectedMeses);
    }
  }



  async function openVigenciaPeriodoAdd() {
    const mesesStr = prompt("Cantidad de meses de vigencia (ej: 12 para un año):");
    if (!mesesStr) return;
    const meses = Number(mesesStr);
    if (!Number.isInteger(meses) || meses < 1 || meses > 120) {
      alert("Ingresá un número entero entre 1 y 120.");
      return;
    }
    const defaultLabel = meses % 12 === 0 && meses >= 12
      ? `${meses / 12} año${meses > 12 ? "s" : ""}`
      : `${meses} meses`;
    const label = prompt("Etiqueta del período (opcional):", defaultLabel);
    try {
      const r = await postJson(`${API}/periodos-vigencia`, { meses, label: label || undefined });
      periodosVigenciaCache = r.periodos || [];
      fillPeriodosVigenciaSelect(periodosVigenciaCache, meses);
      syncCursoVigenciaFields();
    } catch (err) {
      alert(err.message);
    }
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

      tipo: item?.tipo || "",

      modalidad: item?.modalidad || "",

    });

    document.getElementById("cap-c-horas").value = item?.horas ?? "";

    const tieneVig = Boolean(item?.tiene_vigencia || (item?.vigencia_meses && item.vigencia_meses > 0));
    document.getElementById("cap-c-vigencia-chk").checked = tieneVig;
    const periodos = await ensurePeriodosVigencia();
    fillPeriodosVigenciaSelect(periodos, tieneVig ? item?.vigencia_meses : null);
    syncCursoVigenciaFields();

    document.getElementById("cap-c-puntaje").value = item?.puntaje_minimo ?? "";

    document.getElementById("cap-c-eval").checked = Boolean(item?.requiere_evaluacion);
    syncCursoEvalFields();

    document.getElementById("cap-curso-baja")?.classList.toggle("cap-hidden", !cursoEditId);

    setFormError("cap-curso-form-error", "");

    togglePanel("cap-curso-form-panel", true);

  }



  function bindCursoForm() {

    const form = document.getElementById("cap-curso-form");

    if (!form) return;



    document.getElementById("cap-btn-nuevo-curso")?.addEventListener("click", () => openCursoForm(null));

    document.getElementById("cap-c-eval")?.addEventListener("change", syncCursoEvalFields);

    document.getElementById("cap-c-vigencia-chk")?.addEventListener("change", syncCursoVigenciaFields);

    document.getElementById("cap-c-vigencia-periodo")?.addEventListener("change", (e) => {
      const hidden = document.getElementById("cap-c-vigencia");
      if (hidden) hidden.value = e.target.value || "";
    });

    document.getElementById("cap-c-vigencia-add")?.addEventListener("click", () => openVigenciaPeriodoAdd());

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

      payload.tiene_vigencia = document.getElementById("cap-c-vigencia-chk")?.checked || false;

      if (payload.horas) payload.horas = Number(payload.horas);

      if (payload.tiene_vigencia) {
        const meses = Number(document.getElementById("cap-c-vigencia")?.value || 0);
        if (!meses) {
          setFormError("cap-curso-form-error", "Seleccioná el período de vigencia.");
          return;
        }
        payload.vigencia_meses = meses;
      } else {
        payload.tiene_vigencia = false;
        delete payload.vigencia_meses;
      }

      if (!payload.requiere_evaluacion) delete payload.puntaje_minimo;

      else if (payload.puntaje_minimo) payload.puntaje_minimo = Number(payload.puntaje_minimo);

      delete payload.id;

      try {

        if (cursoEditId) {

          await putJson(`${API}/cursos/${cursoEditId}`, payload);

        } else {

          const resolution = await resolveSimilarBeforeCreate({

            tipo: "curso",

            nombre: payload.nombre,

            codigo: payload.codigo,

          });

          if (resolution.action === "cancel") return;

          if (resolution.action === "use") {

            togglePanel("cap-curso-form-panel", false);

            form.reset();

            cursoEditId = null;

            await loadCursos();

            const cursos = window.capCursosCache || [];

            const existente = cursos.find((c) => String(c.id) === String(resolution.item.id));

            if (existente) openCursoForm(existente);

            return;

          }

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



  async function loadProgNombreCatalog() {
    const data = await fetchJson(`${API}/programas`);
    const seen = new Map();
    (data.programas || []).forEach((p) => {
      const nombre = (p.nombre || "").trim();
      if (!nombre) return;
      const key = nombre.toLowerCase();
      if (!seen.has(key)) seen.set(key, nombre);
    });
    progNombreCatalogCache = Array.from(seen.values()).sort((a, b) => a.localeCompare(b, "es"));
    return progNombreCatalogCache;
  }

  function fillProgNombreSelect(currentNombre = "") {
    const sel = document.getElementById("cap-prog-nombre-select");
    if (!sel) return;
    const names = [...progNombreCatalogCache];
    const cur = (currentNombre || "").trim();
    if (cur && !names.some((n) => n.toLowerCase() === cur.toLowerCase())) {
      names.push(cur);
      names.sort((a, b) => a.localeCompare(b, "es"));
    }
    sel.innerHTML = '<option value="">— Seleccionar plan de carrera —</option>';
    names.forEach((nombre) => {
      const opt = document.createElement("option");
      opt.value = nombre;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    sel.innerHTML += '<option value="__nuevo__">+ Crear nombre nuevo…</option>';
    if (cur) sel.value = cur;
  }

  function appendProgNombreOption(nombre) {
    const sel = document.getElementById("cap-prog-nombre-select");
    if (!sel) return;
    const name = (nombre || "").trim();
    if (!name) return;
    const exists = Array.from(sel.options).some((o) => o.value.toLowerCase() === name.toLowerCase());
    if (!exists) {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      const nuevoOpt = sel.querySelector('option[value="__nuevo__"]');
      if (nuevoOpt) sel.insertBefore(opt, nuevoOpt);
      else sel.appendChild(opt);
    }
    sel.value = name;
  }

  async function loadProgPlanCatalog() {
    const data = await fetchJson(`${API}/planes`);
    const seen = new Map();
    (data.planes || []).forEach((p) => {
      const nombre = (p.nombre || "").trim();
      if (!nombre) return;
      const key = nombre.toLowerCase();
      if (!seen.has(key)) seen.set(key, nombre);
    });
    progPlanCatalogCache = Array.from(seen.values()).sort((a, b) => a.localeCompare(b, "es"));
    return progPlanCatalogCache;
  }

  function progPlanesDraftNames() {
    return new Set(progPlanesDraft.map((p) => p.nombre.trim().toLowerCase()).filter(Boolean));
  }

  function fillProgPlanSelect() {
    const sel = document.getElementById("cap-prog-plan-select");
    if (!sel) return;
    const used = progPlanesDraftNames();
    const disponibles = progPlanCatalogCache.filter((n) => !used.has(n.toLowerCase()));
    sel.innerHTML = '<option value="">— Seleccionar plan —</option>';
    disponibles.forEach((nombre) => {
      const opt = document.createElement("option");
      opt.value = nombre;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    sel.innerHTML += '<option value="__nuevo__">+ Crear plan nuevo…</option>';
  }

  function fillDetallePlanSelect(planesActuales = [], selectId = "cap-detalle-plan-select") {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    const used = new Set((planesActuales || []).map((p) => (p.nombre || "").trim().toLowerCase()));
    const disponibles = progPlanCatalogCache.filter((n) => !used.has(n.toLowerCase()));
    sel.innerHTML = '<option value="">— Seleccionar plan —</option>';
    disponibles.forEach((nombre) => {
      const opt = document.createElement("option");
      opt.value = nombre;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    sel.innerHTML += '<option value="__nuevo__">+ Crear plan nuevo…</option>';
  }

  function renderProgPlanesDraft() {
    const tags = document.getElementById("cap-prog-planes-tags");
    if (!tags) return;
    if (!progPlanesDraft.length) {
      tags.innerHTML = "";
      tags.classList.add("cap-hidden");
      return;
    }
    tags.classList.remove("cap-hidden");
    tags.innerHTML = progPlanesDraft.map((p, i) => `
      <span class="cap-prog-plan-tag">
        <span>${escapeHtml(p.nombre)}</span>
        <button type="button" class="cap-prog-plan-tag-rm" data-prog-plan-rm="${i}" title="Quitar"><i class="bi bi-x-lg"></i></button>
      </span>`).join("");
    tags.querySelectorAll("[data-prog-plan-rm]").forEach((btn) => {
      btn.addEventListener("click", () => {
        progPlanesDraft.splice(Number(btn.dataset.progPlanRm), 1);
        renderProgPlanesDraft();
        fillProgPlanSelect();
      });
    });
  }

  function addProgPlanDraft(nombre) {
    const name = (nombre || "").trim();
    if (!name) return false;
    if (progPlanesDraftNames().has(name.toLowerCase())) {
      setFormError("cap-programa-form-error", "Ese plan ya está en la lista");
      return false;
    }
    setFormError("cap-programa-form-error", "");
    progPlanesDraft.push({ nombre: name });
    renderProgPlanesDraft();
    fillProgPlanSelect();
    return true;
  }

  async function resetProgPlanesDraft(programa = null) {
    progPlanesDraft = (programa?.planes || []).map((p) => ({ id: p.id, nombre: p.nombre }));
    try {
      await loadProgPlanCatalog();
    } catch (e) {
      console.error(e);
    }
    renderProgPlanesDraft();
    fillProgPlanSelect();
    togglePanel("cap-prog-plan-quick", false);
    const quickNombre = document.getElementById("cap-prog-plan-quick-nombre");
    if (quickNombre) quickNombre.value = "";
    const sel = document.getElementById("cap-prog-plan-select");
    if (sel) sel.value = "";
  }

  function renderProgramaCardHtml(p, groupPuestoId = "") {
    const tipoLabel = p.tipo === "externo" ? "Externo" : "Interno";
    const badgeClass = p.tipo === "externo" ? "cap-badge--yellow" : "cap-badge--blue";
    const expanded = p.id === programaSeleccionadoId && String(programaSeleccionadoGrupoPuestoId) === String(groupPuestoId);
    const desc = (p.descripcion || "").trim();
    const puestosTxt = (p.puestos || []).map((x) => x.nombre || x.codigo).filter(Boolean).join(" · ");
    return `
    <article class="cap-prog-card${expanded ? " cap-prog-card--expanded" : ""}" data-programa-id="${p.id}" data-group-puesto-id="${groupPuestoId}">
      <div class="cap-prog-card-summary" role="button" tabindex="0" aria-expanded="${expanded}">
        <div class="cap-prog-card-head">
          <h3 class="cap-prog-card-title">${escapeHtml(p.nombre)}</h3>
          <span class="cap-badge ${badgeClass}">${tipoLabel}</span>
        </div>
        <div class="cap-prog-card-stats">
          <span><i class="bi bi-diagram-3"></i> ${p.planes_count || 0} planes</span>
          <span><i class="bi bi-journal-text"></i> ${p.cursos_count || 0} cursos</span>
        </div>
        ${puestosTxt ? `<p class="cap-prog-card-puestos cap-muted">${escapeHtml(puestosTxt)}</p>` : ""}
        ${desc ? `<p class="cap-prog-card-desc">${escapeHtml(desc)}</p>` : ""}
        <div class="cap-prog-card-actions">
          <button type="button" class="cap-btn cap-btn--primary cap-btn--sm" data-prog-toggle="${p.id}">
            ${expanded ? "Cerrar" : "Abrir"}
          </button>
        </div>
      </div>
      <div class="cap-prog-card-detail${expanded ? "" : " cap-hidden"}"></div>
    </article>`;
  }

  function progPuestoOptions(programas) {
    const seen = new Map();
    (programas || []).forEach((prog) => {
      (prog.puestos || []).forEach((p) => {
        if (p?.id && !seen.has(p.id)) {
          seen.set(p.id, { id: p.id, nombre: p.nombre || p.codigo || String(p.id), codigo: p.codigo || "" });
        }
      });
    });
    (metaPuestos || []).forEach((p) => {
      if (p?.id && p.en_uso && !seen.has(p.id)) {
        seen.set(p.id, { id: p.id, nombre: p.nombre, codigo: p.codigo || "" });
      }
    });
    return Array.from(seen.values()).sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), "es"));
  }

  function progFiltroEsTodos(puestoItems) {
    const selected = progFiltros.puestos || [];
    if (!selected.length) return true;
    const allIds = (puestoItems || []).map((p) => String(p.id));
    return allIds.length > 0 && selected.length === allIds.length && allIds.every((id) => selected.includes(id));
  }

  function programasFiltrados() {
    const items = progPuestoOptions(programasCache);
    if (progFiltroEsTodos(items)) return programasCache;
    const set = new Set((progFiltros.puestos || []).map(String));
    return programasCache.filter((prog) => (prog.puestos || []).some((p) => set.has(String(p.id))));
  }

  function renderProgFiltroPuesto(programas) {
    const items = progPuestoOptions(programas);
    const key = items.map((p) => p.id).join(",");
    const el = document.getElementById("cap-prog-filtro-puesto");
    if (el && progFiltroPuestoKey === key && el.querySelector(".cap-multi-btn")) return;
    progFiltroPuestoKey = key;
    renderCapMultiSelect("cap-prog-filtro-puesto", items, "puestos", progFiltros, () => {
      if (programaSeleccionadoId) {
        const visible = programasFiltrados().some((p) => p.id === programaSeleccionadoId);
        if (!visible) {
          programaSeleccionadoId = null;
          programaSeleccionadoGrupoPuestoId = "";
          programaDetalleEditable = false;
        }
      }
      renderProgramasGrid();
    });
  }

  function renderProgramasGrid() {
    const grid = document.getElementById("cap-programas-grid");
    if (!grid) return;
    if (!programasCache.length) {
      grid.innerHTML = '<p class="cap-empty">Todavía no hay planes de carrera. Usá <strong>+ Nuevo plan de carrera</strong>: primero elegí el puesto, después el plan de carrera y los planes.</p>';
      return;
    }
    const visibles = programasFiltrados();
    if (!visibles.length) {
      grid.innerHTML = '<p class="cap-empty">No hay planes de carrera para los puestos seleccionados.</p>';
      return;
    }
    grid.innerHTML = visibles.map((p) => renderProgramaCardHtml(p, "")).join("");
    if (programaSeleccionadoId) {
      const card = document.querySelector(programaCardSelector(programaSeleccionadoId, programaSeleccionadoGrupoPuestoId));
      if (!card) {
        programaSeleccionadoId = null;
        programaSeleccionadoGrupoPuestoId = "";
        return;
      }
      const detailEl = card.querySelector(".cap-prog-card-detail");
      const cached = programasCache.find((prog) => prog.id === programaSeleccionadoId);
      if (detailEl && cached?.planes) {
        renderProgramaDetalleEnCard(cached, detailEl, programaDetalleEditable);
      }
    }
  }

  async function loadProgramas() {
    const grid = document.getElementById("cap-programas-grid");
    if (!grid) return;
    grid.innerHTML = '<p class="cap-loading">Cargando...</p>';
    const tipo = document.getElementById("cap-prog-filtro-tipo")?.value || "";
    const qs = tipo ? `?tipo=${encodeURIComponent(tipo)}` : "";
    const data = await fetchJson(`${API}/programas${qs}`);
    programasCache = data.programas || [];
    renderProgFiltroPuesto(programasCache);
    renderProgramasGrid();
  }

  function programaCardSelector(programaId, groupPuestoId) {
    if (groupPuestoId !== undefined && groupPuestoId !== null && String(groupPuestoId) !== "") {
      return `.cap-prog-card[data-programa-id="${programaId}"][data-group-puesto-id="${groupPuestoId}"]`;
    }
    return `.cap-prog-card[data-programa-id="${programaId}"]`;
  }

  function collapsePrograma() {
    programaSeleccionadoId = null;
    programaSeleccionadoGrupoPuestoId = "";
    programaDetalleEditable = false;
    loadProgramas().catch(console.error);
  }

  function refreshProgramaDetalle() {
    if (!programaSeleccionadoId) return;
    const card = document.querySelector(programaCardSelector(programaSeleccionadoId, programaSeleccionadoGrupoPuestoId));
    const detailEl = card?.querySelector(".cap-prog-card-detail");
    const programa = programasCache.find((p) => p.id === programaSeleccionadoId);
    if (detailEl && programa?.planes) {
      renderProgramaDetalleEnCard(programa, detailEl, programaDetalleEditable);
    }
  }

  async function togglePrograma(programaId, groupPuestoId) {
    const gid = groupPuestoId == null ? "" : String(groupPuestoId);
    if (programaSeleccionadoId === programaId && String(programaSeleccionadoGrupoPuestoId) === gid) {
      collapsePrograma();
      return;
    }
    await selectPrograma(programaId, { groupPuestoId: gid });
  }

  function renderProgramaDetalleEnCard(programa, containerEl, editable = false) {
    const tipoTxt = programa.tipo === "externo" ? "Externo" : "Interno";
    const metaRows = [
      programa.codigo ? `<div class="cap-prog-detail-row"><span class="cap-prog-detail-label">Código</span><span>${escapeHtml(programa.codigo)}</span></div>` : "",
      editable ? "" : `<div class="cap-prog-detail-row"><span class="cap-prog-detail-label">Tipo</span><span>${tipoTxt}</span></div>`,
      programa.estado
        ? `<div class="cap-prog-detail-row"><span class="cap-prog-detail-label">Estado</span><span>${escapeHtml(programaEstadoLabel(programa.estado))}</span></div>`
        : "",
    ].filter(Boolean).join("");
    const esExterno = programa.tipo === "externo";
    const detallesEditable = `
      <div class="cap-prog-detail-edit">
        <div class="cap-prog-detail-edit-field">
          <label class="cap-label">Tipo</label>
          <div class="cap-radio-row" data-prog-tipo-edit="${programa.id}">
            <label class="cap-radio"><input type="radio" name="cap-prog-tipo-edit-${programa.id}" value="interno" ${esExterno ? "" : "checked"}> Interno</label>
            <label class="cap-radio"><input type="radio" name="cap-prog-tipo-edit-${programa.id}" value="externo" ${esExterno ? "checked" : ""}> Externo</label>
          </div>
          <p class="cap-muted">Si el plan de carrera es externo, la empresa que lo dicta se indica al cerrar el cronograma.</p>
        </div>
        <div class="cap-prog-detail-edit-field">
          <label class="cap-label" for="cap-prog-desc-edit-${programa.id}">Descripción</label>
          <textarea class="cap-input cap-textarea" id="cap-prog-desc-edit-${programa.id}" rows="2" placeholder="Opcional">${escapeHtml(programa.descripcion || "")}</textarea>
        </div>
        <div class="cap-input-group">
          <button type="button" class="cap-btn cap-btn--primary cap-btn--sm" data-prog-guardar-detalle="${programa.id}">Guardar detalles</button>
        </div>
        <p class="cap-form-hint cap-form-hint--error" id="cap-prog-detalle-error-${programa.id}"></p>
      </div>`;
    const puestosId = `cap-programa-puestos-detalle-${programa.id}`;
    const puestosSection = editable
      ? `<div class="cap-check-grid" id="${puestosId}"></div>
          <p class="cap-form-hint cap-form-hint--error" id="cap-programa-puestos-error-${programa.id}"></p>
          <button type="button" class="cap-btn cap-btn--primary cap-btn--sm cap-mt" data-prog-guardar-puestos="${programa.id}">Guardar puestos</button>`
      : `<div class="cap-prog-puestos-readonly" id="${puestosId}"></div>`;
    containerEl.innerHTML = `
      <div class="cap-prog-detail-inner${editable ? " cap-prog-detail-inner--editable" : ""}">
        <div class="cap-prog-detail-head">
          <div class="cap-prog-detail-head-main">
            <h4 class="cap-prog-detail-title">Puesto → Plan de carrera → Planes</h4>
            ${editable
              ? `<div class="cap-input-group cap-prog-nombre-edit">
                   <input type="text" id="cap-prog-nombre-edit-${programa.id}" class="cap-input" value="${escapeHtml(programa.nombre)}" maxlength="200" aria-label="Nombre del plan de carrera">
                   <button type="button" class="cap-btn cap-btn--primary cap-btn--sm" data-prog-guardar-nombre="${programa.id}">Guardar nombre</button>
                 </div>
                 <p class="cap-form-hint cap-form-hint--error" id="cap-prog-nombre-error-${programa.id}"></p>`
              : `<p class="cap-muted">${escapeHtml(programa.nombre)}</p>`}
          </div>
          <div class="cap-toolbar-actions">
            ${editable
              ? `<button type="button" class="cap-btn cap-btn--ghost cap-btn--sm" data-prog-edit-done="${programa.id}"><i class="bi bi-check-lg"></i> Listo</button>
                 <button type="button" class="cap-btn cap-btn--primary cap-btn--sm" data-prog-add-plan><i class="bi bi-plus-lg"></i> Agregar plan</button>
                 <button type="button" class="cap-btn cap-btn--danger cap-btn--sm" data-prog-eliminar="${programa.id}"><i class="bi bi-trash"></i> Eliminar</button>`
              : `<button type="button" class="cap-btn cap-btn--ghost cap-btn--sm" data-prog-edit="${programa.id}"><i class="bi bi-pencil"></i> Editar</button>`}
          </div>
        </div>
        ${editable ? detallesEditable : (programa.descripcion ? `<p class="cap-prog-detail-desc">${escapeHtml(programa.descripcion)}</p>` : "")}
        <div class="cap-prog-detail-meta">${metaRows}</div>
        <div class="cap-prog-detail-puestos">
          <h4 class="cap-subtitle">1. Puestos de los que cuelga</h4>
          ${puestosSection}
        </div>
        <h4 class="cap-subtitle">2. Planes y cursos</h4>
        <div data-prog-planes-wrap></div>
      </div>`;
    if (editable) {
      renderPuestosChecks(puestosId, (programa.puestos || []).map((p) => p.id));
    } else {
      renderPuestosReadOnly(puestosId, programa.puestos || []);
    }
    const planesWrap = containerEl.querySelector("[data-prog-planes-wrap]");
    renderProgramaPlanes(programa, planesWrap, editable);
    containerEl.querySelector("[data-prog-add-plan]")?.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const sel = containerEl.querySelector(`#cap-detalle-plan-select-${programa.id}`);
      sel?.focus();
      sel?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
    // Solo puestos vigentes (con personas activas) + los ya seleccionados en el programa.
    const puestos = (metaPuestos || []).filter(
      (p) => p.en_uso || selected.has(String(p.id))
    );
    if (!puestos.length) {
      el.innerHTML = '<p class="cap-empty">No hay puestos vigentes. Asigná puestos a las personas en <strong>Personas</strong> o importá el padrón actualizado.</p>';
      return;
    }
    el.innerHTML = puestos.map((p) => `
      <label class="cap-check">
        <input type="checkbox" value="${p.id}" ${selected.has(String(p.id)) ? "checked" : ""}>
        <span>${escapeHtml(p.nombre)}</span>
      </label>`).join("");
  }

  function renderPuestosReadOnly(containerId, puestos = []) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!puestos.length) {
      el.innerHTML = '<p class="cap-empty">Ningún puesto asignado.</p>';
      return;
    }
    el.innerHTML = `<ul class="cap-prog-puestos-list">${puestos.map((p) =>
      `<li>${escapeHtml(p.nombre)}</li>`
    ).join("")}</ul>`;
  }

  function selectedPuestoIds(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`))
      .map((inp) => Number(inp.value));
  }

  async function selectPrograma(programaId, { resetEditMode = true, groupPuestoId } = {}) {
    programaSeleccionadoId = programaId;
    if (groupPuestoId !== undefined) programaSeleccionadoGrupoPuestoId = String(groupPuestoId);
    if (resetEditMode) programaDetalleEditable = false;
    await loadProgramas();
    const card = document.querySelector(programaCardSelector(programaId, programaSeleccionadoGrupoPuestoId));
    const detailEl = card?.querySelector(".cap-prog-card-detail");
    if (!detailEl) return;
    detailEl.classList.remove("cap-hidden");
    detailEl.innerHTML = '<div class="cap-loading">Cargando estructura...</div>';
    const data = await fetchJson(`${API}/programas/${programaId}`);
    const programa = data.programa;
    programasCache = programasCache.map((p) => (p.id === programa.id ? { ...p, ...programa } : p));
    renderProgramaDetalleEnCard(programa, detailEl, programaDetalleEditable);
    card?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderProgramaPlanes(programa, planesEl, editable = false) {
    if (!planesEl) return;
    const planes = programa.planes || [];
    const allCursos = window.capCursosCache || [];
    const planesHtml = planes.length ? planes.map((plan) => {
      const usados = new Set((plan.cursos || []).map((c) => Number(c.curso_id)));
      const disponibles = allCursos.filter((c) => !usados.has(Number(c.id)));
      const cursosHtml = (plan.cursos || []).map((c, i) => {
        const badges = (c.tambien_en || []).map((p) => `<span class="cap-badge cap-badge--soft">También en: ${escapeHtml(p.nombre)}</span>`).join(" ");
        const quitarBtn = editable
          ? `<button type="button" class="cap-btn cap-btn--sm cap-btn--danger" data-del-plan-curso="${c.id}" title="Quitar"><i class="bi bi-trash"></i></button>`
          : "";
        return `<li class="cap-plan-curso${editable ? "" : " cap-plan-curso--readonly"}">
          <span class="cap-col-num">${i + 1}</span>
          <span>${escapeHtml(c.curso_codigo)} — ${escapeHtml(c.curso_nombre)} ${badges}</span>
          ${quitarBtn}
        </li>`;
      }).join("") || `<li class="cap-empty">${editable ? "Sin cursos en este plan. Elegí uno abajo y pulsá +" : "Sin cursos en este plan. Pulsá Editar para agregarlos."}</li>`;
      const delPlanBtn = editable
        ? `<button type="button" class="cap-btn cap-btn--sm cap-btn--danger" data-del-plan="${plan.id}" title="Eliminar plan"><i class="bi bi-trash"></i></button>`
        : "";
      const addCursoRow = editable
        ? `<div class="cap-input-group">
          <select class="cap-input" data-plan-curso-select="${plan.id}">
            <option value="">— Agregar curso —</option>
            ${disponibles.map((c) => `<option value="${c.id}">${escapeHtml(c.codigo)} — ${escapeHtml(c.nombre)}</option>`).join("")}
          </select>
          <button type="button" class="cap-btn cap-btn--primary" data-add-plan-curso="${plan.id}"><i class="bi bi-plus-lg"></i></button>
        </div>
        ${!allCursos.length ? '<p class="cap-empty">No hay cursos en el catálogo. Cargalos en Cursos y catálogos.</p>' : (!disponibles.length ? '<p class="cap-empty">Todos los cursos del catálogo ya están en este plan.</p>' : "")}`
        : "";
      return `<section class="cap-plan-block" data-plan-id="${plan.id}">
        <div class="cap-plan-head">
          <h4>${escapeHtml(plan.nombre)}</h4>
          ${delPlanBtn}
        </div>
        <ul class="cap-plan-cursos">${cursosHtml}</ul>
        ${addCursoRow}
      </section>`;
    }).join("") : `<p class="cap-empty">${editable ? "Este plan de carrera no tiene planes. Agregá el primero abajo." : "Este plan de carrera no tiene planes."}</p>`;

    const planSelectId = `cap-detalle-plan-select-${programa.id}`;
    const planQuickId = `cap-detalle-plan-quick-${programa.id}`;
    const planQuickNombreId = `cap-detalle-plan-quick-nombre-${programa.id}`;

    const addPlanRow = editable
      ? `<div class="cap-prog-add-plan-row">
        <label class="cap-label" for="${planSelectId}">Agregar plan</label>
        <div class="cap-input-group">
          <select class="cap-input" id="${planSelectId}" aria-label="Seleccionar plan">
            <option value="">— Seleccionar plan —</option>
          </select>
          <button type="button" class="cap-btn cap-btn--icon" data-detalle-plan-add title="Agregar plan"><i class="bi bi-plus-lg"></i></button>
        </div>
        <div class="cap-quick-form cap-hidden" id="${planQuickId}">
          <p class="cap-quick-form-title">Nuevo plan</p>
          <input class="cap-input" id="${planQuickNombreId}" placeholder="Ej. Seguridad, Técnico, Liderazgo" maxlength="150">
          <div class="cap-form-actions">
            <button type="button" class="cap-btn cap-btn--ghost" data-detalle-plan-quick-cancel>Cancelar</button>
            <button type="button" class="cap-btn cap-btn--primary" data-detalle-plan-quick-save>Agregar plan</button>
          </div>
        </div>
      </div>`
      : "";

    planesEl.innerHTML = `${planesHtml}${addPlanRow}`;

    if (editable) {
      loadProgPlanCatalog()
        .then(() => fillDetallePlanSelect(planes, planSelectId))
        .catch(console.error);
    }

    planesEl.querySelectorAll("[data-add-plan-curso]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const planId = Number(btn.dataset.addPlanCurso);
        const sel = planesEl.querySelector(`[data-plan-curso-select="${planId}"]`);
        const cursoId = Number(sel?.value || 0);
        if (!cursoId) {
          alert("Elegí un curso de la lista antes de agregarlo al plan.");
          sel?.focus();
          return;
        }
        try {
          await postJson(`${API}/planes/${planId}/cursos`, { curso_id: cursoId });
          await selectPrograma(programaSeleccionadoId, { resetEditMode: false });
        } catch (err) {
          alert(err.message);
        }
      });
    });
    planesEl.querySelectorAll("[data-del-plan-curso]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!confirm("¿Quitar este curso del plan?")) return;
        try {
          await deleteJson(`${API}/plan-cursos/${btn.dataset.delPlanCurso}`);
          await selectPrograma(programaSeleccionadoId, { resetEditMode: false });
        } catch (err) {
          alert(err.message);
        }
      });
    });
    planesEl.querySelectorAll("[data-del-plan]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!confirm("¿Eliminar este plan y sus cursos?")) return;
        try {
          await deleteJson(`${API}/planes/${btn.dataset.delPlan}`);
          await selectPrograma(programaSeleccionadoId, { resetEditMode: false });
        } catch (err) {
          alert(err.message);
        }
      });
    });

    async function agregarPlanDetalle(nombre) {
      const name = (nombre || "").trim();
      if (!name || !programaSeleccionadoId) return;
      await postJson(`${API}/programas/${programaSeleccionadoId}/planes`, { nombre: name });
      await selectPrograma(programaSeleccionadoId, { resetEditMode: false });
    }

    if (!editable) return;

    planesEl.querySelector("[data-detalle-plan-add]")?.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const sel = document.getElementById(planSelectId);
      const val = sel?.value || "";
      if (val === "__nuevo__") {
        togglePanel(planQuickId, true);
        document.getElementById(planQuickNombreId)?.focus();
        return;
      }
      if (!val) return;
      try {
        await agregarPlanDetalle(val);
        togglePanel(planQuickId, false);
      } catch (err) {
        alert(err.message);
      }
    });
    document.getElementById(planSelectId)?.addEventListener("change", () => {
      const val = document.getElementById(planSelectId)?.value;
      if (val === "__nuevo__") {
        togglePanel(planQuickId, true);
        document.getElementById(planQuickNombreId)?.focus();
      }
    });
    planesEl.querySelector("[data-detalle-plan-quick-cancel]")?.addEventListener("click", (ev) => {
      ev.stopPropagation();
      togglePanel(planQuickId, false);
      const sel = document.getElementById(planSelectId);
      if (sel) sel.value = "";
      const inp = document.getElementById(planQuickNombreId);
      if (inp) inp.value = "";
    });
    planesEl.querySelector("[data-detalle-plan-quick-save]")?.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const nombre = document.getElementById(planQuickNombreId)?.value.trim();
      if (!nombre) return;
      try {
        await agregarPlanDetalle(nombre);
        togglePanel(planQuickId, false);
        const inp = document.getElementById(planQuickNombreId);
        if (inp) inp.value = "";
      } catch (err) {
        alert(err.message);
      }
    });
  }

  async function loadProgEmpresas() {
    const data = await fetchJson(`${API}/empresas-capacitadoras`);
    fillSelect(
      "cap-prog-empresa",
      data.empresas_capacitadoras || data.empresas || [],
      "— Seleccionar empresa —"
    );
  }

  function toggleProgEmpresa() {
    const wrap = document.getElementById("cap-prog-empresa-wrap");
    const sel = document.getElementById("cap-prog-empresa");
    if (!wrap || !sel) return;
    // La empresa externa se define al cerrar el cronograma, no al crear el programa.
    wrap.classList.add("cap-hidden");
    sel.required = false;
    sel.value = "";
    togglePanel("cap-prog-empresa-quick", false);
    toggleProgPlanesSection();
  }

  function toggleProgPlanesSection() {
    const tipo = document.querySelector('#cap-programa-form input[name="tipo"]:checked')?.value;
    const wrap = document.getElementById("cap-prog-planes-wrap");
    if (!wrap) return;
    wrap.classList.toggle("cap-hidden", !tipo);
  }

  async function abrirFormularioPrograma(programa = null) {
    if (!metaPuestos.length) {
      try { await loadPuestosOptions(); } catch (e) { console.error(e); }
    }
    if (!(window.capCursosCache || []).length) {
      try {
        const data = await fetchJson(`${API}/cursos`);
        window.capCursosCache = data.cursos || [];
      } catch (e) { console.error(e); }
    }
    openProgramaForm(programa);
    document.getElementById("cap-programa-form-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function openProgramaForm(programa = null) {
    const form = document.getElementById("cap-programa-form");
    if (form) form.reset();
    setFormError("cap-programa-form-error", "");
    document.getElementById("cap-prog-id").value = programa?.id || "";
    document.getElementById("cap-prog-codigo").value = programa?.codigo || "";
    document.getElementById("cap-prog-descripcion").value = programa?.descripcion || "";
    const tipo = programa?.tipo || "interno";
    form.querySelectorAll('input[name="tipo"]').forEach((inp) => {
      inp.checked = inp.value === tipo;
    });
    renderPuestosChecks("cap-prog-puestos", (programa?.puestos || []).map((p) => p.id));
    document.getElementById("cap-programa-submit").textContent = programa ? "Guardar cambios" : "Crear plan de carrera";
    togglePanel("cap-prog-empresa-quick", false);
    togglePanel("cap-prog-plan-quick", false);
    togglePanel("cap-prog-nombre-quick", false);
    resetProgPlanesDraft(programa);
    Promise.all([
      loadProgNombreCatalog().then(() => fillProgNombreSelect(programa?.nombre || "")),
      loadProgEmpresas().then(() => {
        const sel = document.getElementById("cap-prog-empresa");
        if (sel && programa?.empresa_capacitadora_id) {
          sel.value = String(programa.empresa_capacitadora_id);
        }
        toggleProgEmpresa();
      }),
    ]).catch(console.error);
    togglePanel("cap-programa-form-panel", true);
    toggleProgPlanesSection();
    document.getElementById("cap-prog-nombre-select")?.focus();
  }

  function bindProgramaForm() {
    document.getElementById("cap-btn-nuevo-programa")?.addEventListener("click", () => {
      abrirFormularioPrograma().catch(console.error);
    });
    document.getElementById("cap-btn-importar-programas")?.addEventListener("click", () => {
      document.getElementById("cap-import-programas-file")?.click();
    });
    document.getElementById("cap-import-programas-file")?.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const r = await uploadFile(`${API}/programas/importar`, file);
        const partes = [
          `${r.creados || 0} planes de carrera nuevos`,
          `${r.actualizados || 0} actualizados`,
          `${r.planes_agregados || 0} planes`,
          `${r.puestos_agregados || 0} puestos`,
        ];
        if (r.cursos_agregados) partes.push(`${r.cursos_agregados} cursos`);
        let msg = `Importación: ${partes.join(", ")}.`;
        if (r.errores?.length) {
          msg += "\n\nAvisos:\n" + r.errores.slice(0, 40).join("\n");
          if (r.errores.length > 40) msg += `\n… y ${r.errores.length - 40} más`;
        }
        alert(msg);
        await loadProgramas();
      } catch (err) {
        alert(err.message);
      }
      e.target.value = "";
    });
    document.getElementById("cap-programa-cancel")?.addEventListener("click", () => {
      togglePanel("cap-programa-form-panel", false);
      togglePanel("cap-prog-empresa-quick", false);
      togglePanel("cap-prog-nombre-quick", false);
    });
    document.querySelectorAll('#cap-programa-form input[name="tipo"]').forEach((inp) => {
      inp.addEventListener("change", toggleProgEmpresa);
    });
    document.getElementById("cap-prog-nombre-add")?.addEventListener("click", () => {
      togglePanel("cap-prog-nombre-quick", true);
      document.getElementById("cap-prog-nombre-quick-nombre")?.focus();
    });
    document.getElementById("cap-prog-nombre-select")?.addEventListener("change", () => {
      const val = document.getElementById("cap-prog-nombre-select")?.value;
      if (val === "__nuevo__") {
        togglePanel("cap-prog-nombre-quick", true);
        document.getElementById("cap-prog-nombre-quick-nombre")?.focus();
      }
    });
    document.getElementById("cap-prog-nombre-quick-cancel")?.addEventListener("click", () => {
      togglePanel("cap-prog-nombre-quick", false);
      const sel = document.getElementById("cap-prog-nombre-select");
      if (sel?.value === "__nuevo__") sel.value = "";
      const inp = document.getElementById("cap-prog-nombre-quick-nombre");
      if (inp) inp.value = "";
    });
    document.getElementById("cap-prog-nombre-quick-save")?.addEventListener("click", () => {
      const nombre = document.getElementById("cap-prog-nombre-quick-nombre")?.value.trim();
      if (!nombre) return;
      appendProgNombreOption(nombre);
      document.getElementById("cap-prog-nombre-quick-nombre").value = "";
      togglePanel("cap-prog-nombre-quick", false);
    });
    document.getElementById("cap-prog-empresa-add")?.addEventListener("click", () => {
      togglePanel("cap-prog-empresa-quick", true);
      document.getElementById("cap-prog-empresa-quick-nombre")?.focus();
    });
    document.getElementById("cap-prog-empresa-quick-cancel")?.addEventListener("click", () => {
      togglePanel("cap-prog-empresa-quick", false);
    });
    document.getElementById("cap-prog-empresa-quick-save")?.addEventListener("click", async () => {
      const nombre = document.getElementById("cap-prog-empresa-quick-nombre")?.value.trim();
      if (!nombre) return;
      try {
        const resolution = await resolveSimilarBeforeCreate({ tipo: "empresa_capacitadora", nombre });
        if (resolution.action === "cancel") return;
        if (resolution.action === "use") {
          appendEncSelectOption("cap-prog-empresa", resolution.item);
          document.getElementById("cap-prog-empresa-quick-nombre").value = "";
          togglePanel("cap-prog-empresa-quick", false);
          return;
        }
        const data = await postJson(`${API}/empresas-capacitadoras`, { nombre });
        appendEncSelectOption("cap-prog-empresa", data.empresa_capacitadora);
        document.getElementById("cap-prog-empresa-quick-nombre").value = "";
        togglePanel("cap-prog-empresa-quick", false);
      } catch (err) {
        alert(err.message);
      }
    });
    document.getElementById("cap-prog-filtro-tipo")?.addEventListener("change", () => {
      collapsePrograma();
      loadProgramas().catch(console.error);
    });
    document.getElementById("cap-programas-grid")?.addEventListener("click", async (ev) => {
      const editBtn = ev.target.closest("[data-prog-edit]");
      if (editBtn) {
        ev.stopPropagation();
        const id = Number(editBtn.dataset.progEdit);
        programaDetalleEditable = true;
        if (!(window.capCursosCache || []).length) {
          try {
            const cursosData = await fetchJson(`${API}/cursos`);
            window.capCursosCache = cursosData.cursos || [];
          } catch (e) { console.error(e); }
        }
        const data = await fetchJson(`${API}/programas/${id}`);
        programasCache = programasCache.map((p) => (p.id === data.programa.id ? { ...p, ...data.programa } : p));
        refreshProgramaDetalle();
        return;
      }
      const editDoneBtn = ev.target.closest("[data-prog-edit-done]");
      if (editDoneBtn) {
        ev.stopPropagation();
        programaDetalleEditable = false;
        togglePanel("cap-programa-form-panel", false);
        refreshProgramaDetalle();
        return;
      }
      const guardarBtn = ev.target.closest("[data-prog-guardar-puestos]");
      if (guardarBtn) {
        ev.stopPropagation();
        const id = Number(guardarBtn.dataset.progGuardarPuestos);
        setFormError(`cap-programa-puestos-error-${id}`, "");
        const puestoIds = selectedPuestoIds(`cap-programa-puestos-detalle-${id}`);
        const prev = (programasCache.find((p) => p.id === id)?.puestos || []).length;
        if (!puestoIds.length && prev > 0) {
          if (!confirm("Vas a quitar TODOS los puestos de este plan de carrera. ¿Continuar?")) return;
        }
        try {
          const body = { puesto_ids: puestoIds };
          if (!puestoIds.length && prev > 0) body.clear_puestos = true;
          await putJson(`${API}/programas/${id}`, body);
          await selectPrograma(id, { resetEditMode: false });
        } catch (err) {
          setFormError(`cap-programa-puestos-error-${id}`, err.message);
        }
        return;
      }
      const guardarNombreBtn = ev.target.closest("[data-prog-guardar-nombre]");
      if (guardarNombreBtn) {
        ev.stopPropagation();
        const id = Number(guardarNombreBtn.dataset.progGuardarNombre);
        const nombre = (document.getElementById(`cap-prog-nombre-edit-${id}`)?.value || "").trim();
        setFormError(`cap-prog-nombre-error-${id}`, "");
        if (!nombre) {
          setFormError(`cap-prog-nombre-error-${id}`, "El nombre es obligatorio");
          return;
        }
        try {
          await putJson(`${API}/programas/${id}`, { nombre });
          await selectPrograma(id, { resetEditMode: false });
        } catch (err) {
          setFormError(`cap-prog-nombre-error-${id}`, err.message);
        }
        return;
      }
      const guardarDetalleBtn = ev.target.closest("[data-prog-guardar-detalle]");
      if (guardarDetalleBtn) {
        ev.stopPropagation();
        const id = Number(guardarDetalleBtn.dataset.progGuardarDetalle);
        setFormError(`cap-prog-detalle-error-${id}`, "");
        const tipo = document.querySelector(`[data-prog-tipo-edit="${id}"] input[type="radio"]:checked`)?.value || "interno";
        const descripcion = (document.getElementById(`cap-prog-desc-edit-${id}`)?.value || "").trim();
        const body = { tipo, descripcion, empresa_capacitadora_id: null };
        try {
          await putJson(`${API}/programas/${id}`, body);
          await selectPrograma(id, { resetEditMode: false });
        } catch (err) {
          setFormError(`cap-prog-detalle-error-${id}`, err.message);
        }
        return;
      }
      const eliminarBtn = ev.target.closest("[data-prog-eliminar]");
      if (eliminarBtn) {
        ev.stopPropagation();
        const id = Number(eliminarBtn.dataset.progEliminar);
        if (!confirm("¿Eliminar este plan de carrera? Esta acción no se puede deshacer.")) return;
        try {
          await deleteJson(`${API}/programas/${id}`);
          collapsePrograma();
        } catch (err) {
          alert(err.message);
        }
        return;
      }
      if (ev.target.closest(".cap-prog-card-detail")) return;
      const toggleBtn = ev.target.closest("[data-prog-toggle]");
      if (toggleBtn) {
        ev.stopPropagation();
        const card = toggleBtn.closest("[data-programa-id]");
        togglePrograma(Number(toggleBtn.dataset.progToggle), card?.dataset.groupPuestoId).catch(console.error);
        return;
      }
      const summary = ev.target.closest(".cap-prog-card-summary");
      if (summary && !ev.target.closest("button, input, select, textarea, a, label")) {
        const card = summary.closest("[data-programa-id]");
        if (card) togglePrograma(Number(card.dataset.programaId), card.dataset.groupPuestoId).catch(console.error);
      }
    });
    document.getElementById("cap-programas-grid")?.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      const summary = ev.target.closest(".cap-prog-card-summary");
      if (!summary) return;
      ev.preventDefault();
      const card = summary.closest("[data-programa-id]");
      if (card) togglePrograma(Number(card.dataset.programaId), card.dataset.groupPuestoId).catch(console.error);
    });
    document.getElementById("cap-prog-plan-add")?.addEventListener("click", () => {
      const sel = document.getElementById("cap-prog-plan-select");
      const val = sel?.value || "";
      if (val === "__nuevo__") {
        togglePanel("cap-prog-plan-quick", true);
        document.getElementById("cap-prog-plan-quick-nombre")?.focus();
        return;
      }
      if (!val) {
        togglePanel("cap-prog-plan-quick", true);
        document.getElementById("cap-prog-plan-quick-nombre")?.focus();
        return;
      }
      addProgPlanDraft(val);
      if (sel) sel.value = "";
    });
    document.getElementById("cap-prog-plan-select")?.addEventListener("change", () => {
      const val = document.getElementById("cap-prog-plan-select")?.value;
      if (val === "__nuevo__") {
        togglePanel("cap-prog-plan-quick", true);
        document.getElementById("cap-prog-plan-quick-nombre")?.focus();
      }
    });
    document.getElementById("cap-prog-plan-quick-cancel")?.addEventListener("click", () => {
      togglePanel("cap-prog-plan-quick", false);
      const sel = document.getElementById("cap-prog-plan-select");
      if (sel) sel.value = "";
      const inp = document.getElementById("cap-prog-plan-quick-nombre");
      if (inp) inp.value = "";
    });
    document.getElementById("cap-prog-plan-quick-save")?.addEventListener("click", () => {
      const nombre = document.getElementById("cap-prog-plan-quick-nombre")?.value.trim();
      if (!nombre) return;
      if (addProgPlanDraft(nombre)) {
        togglePanel("cap-prog-plan-quick", false);
        document.getElementById("cap-prog-plan-quick-nombre").value = "";
        const sel = document.getElementById("cap-prog-plan-select");
        if (sel) sel.value = "";
      }
    });
    document.getElementById("cap-programa-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      setFormError("cap-programa-form-error", "");
      const body = formToObject(e.target);
      body.puesto_ids = selectedPuestoIds("cap-prog-puestos");
      body.tipo = e.target.querySelector('input[name="tipo"]:checked')?.value || "interno";
      delete body.empresa_capacitadora_id;
      if (!body.nombre || body.nombre === "__nuevo__") {
        setFormError("cap-programa-form-error", "Seleccioná o agregá el nombre del plan de carrera");
        return;
      }
      if (!body.puesto_ids.length) {
        setFormError("cap-programa-form-error", "Seleccioná al menos un puesto. El plan de carrera cuelga del puesto.");
        return;
      }
      if (!progPlanesDraft.length) {
        setFormError("cap-programa-form-error", "Agregá al menos un plan al plan de carrera");
        return;
      }
      body.planes = progPlanesDraft.map((p, i) => ({
        ...(p.id ? { id: p.id } : {}),
        nombre: p.nombre,
        orden: i + 1,
      }));
      const id = body.id ? Number(body.id) : null;
      delete body.id;
      try {
        const data = id
          ? await putJson(`${API}/programas/${id}`, body)
          : await postJson(`${API}/programas`, body);
        await loadProgramas();
        if (id && data.programa?.id) {
          togglePanel("cap-programa-form-panel", false);
          e.target.reset();
          progPlanesDraft = [];
          await selectPrograma(data.programa.id);
        } else {
          e.target.reset();
          document.getElementById("cap-prog-id").value = "";
          progPlanesDraft = [];
          await resetProgPlanesDraft();
          toggleProgPlanesSection();
          setFormError("cap-programa-form-error", "");
          collapsePrograma();
          document.getElementById("cap-prog-nombre-select")?.focus();
        }
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
  let asistenciaEsExterno = false;

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

  async function fillCierreEmpresaSelect(selectedId = "") {
    const sel = document.getElementById("cap-cierre-empresa");
    if (!sel) return;
    try {
      const data = await fetchJson(`${API}/empresas-capacitadoras`);
      const items = data.empresas_capacitadoras || data.empresas || [];
      sel.innerHTML = '<option value="">— Seleccionar empresa —</option>';
      items.forEach((it) => {
        const opt = document.createElement("option");
        opt.value = it.id;
        opt.textContent = it.codigo ? `${it.codigo} — ${it.nombre}` : it.nombre;
        sel.appendChild(opt);
      });
      if (selectedId) sel.value = String(selectedId);
    } catch (e) {
      console.error(e);
      sel.innerHTML = '<option value="">— Seleccionar empresa —</option>';
    }
  }

  function toggleCierreEmpresaRow(show, selectedId = "") {
    const row = document.getElementById("cap-cierre-empresa-row");
    const sel = document.getElementById("cap-cierre-empresa");
    if (!row) return;
    row.classList.toggle("cap-hidden", !show);
    if (sel) {
      sel.required = !!show;
      if (!show) {
        sel.value = "";
        togglePanel("cap-cierre-empresa-quick", false);
      }
    }
    if (show) fillCierreEmpresaSelect(selectedId).catch(console.error);
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
    asistenciaEsExterno = data.tipo === "externo" || String(data.origen || "").startsWith("extern");
    toggleCierreEmpresaRow(asistenciaEsExterno, data.empresa_capacitadora_id || "");
    const capEl = document.getElementById("cap-cierre-capacitador");
    const lugEl = document.getElementById("cap-cierre-lugar");
    const linkEl = document.getElementById("cap-cierre-link");
    if (capEl) capEl.value = data.instructor || "";
    if (lugEl) lugEl.value = data.lugar || "";
    if (linkEl) linkEl.value = data.link_virtual || "";
    const fechaRealEl = document.getElementById("cap-cierre-fecha");
    if (fechaRealEl) {
      const hoyIso = new Date().toISOString().slice(0, 10);
      fechaRealEl.value = data.fecha_realizacion || hoyIso;
    }
    const fechaHintEl = document.getElementById("cap-cierre-fecha-hint");
    if (fechaHintEl) {
      const mes = data.mes || (data.fecha ? String(data.fecha).slice(0, 7) : "");
      if (mes) {
        const [yy, mm] = mes.split("-");
        fechaHintEl.textContent = `Programado para ${MESES[Number(mm) - 1] || ""} ${yy}`;
      } else {
        fechaHintEl.textContent = "";
      }
    }
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
    asistenciaEsExterno = false;
    toggleCierreEmpresaRow(false);
    document.getElementById("cap-asistencia-modal")?.classList.add("cap-hidden");
  }

  function bindAsistenciaModal() {
    ["cap-asistencia-cerrar", "cap-asistencia-cancel", "cap-asistencia-backdrop"].forEach((id) => {
      document.getElementById(id)?.addEventListener("click", closeAsistenciaModal);
    });
    document.getElementById("cap-cierre-empresa-add")?.addEventListener("click", () => {
      togglePanel("cap-cierre-empresa-quick", true);
      document.getElementById("cap-cierre-empresa-quick-nombre")?.focus();
    });
    document.getElementById("cap-cierre-empresa-quick-cancel")?.addEventListener("click", () => {
      togglePanel("cap-cierre-empresa-quick", false);
    });
    document.getElementById("cap-cierre-empresa-quick-save")?.addEventListener("click", async () => {
      const nombre = document.getElementById("cap-cierre-empresa-quick-nombre")?.value.trim();
      if (!nombre) {
        alert("Indicá el nombre de la empresa capacitadora");
        return;
      }
      try {
        const resolution = await resolveSimilarBeforeCreate({ tipo: "empresa_capacitadora", nombre });
        if (resolution.action === "cancel") return;
        if (resolution.action === "use") {
          appendEncSelectOption("cap-cierre-empresa", resolution.item);
          document.getElementById("cap-cierre-empresa-quick-nombre").value = "";
          togglePanel("cap-cierre-empresa-quick", false);
          return;
        }
        const data = await postJson(`${API}/empresas-capacitadoras`, { nombre });
        appendEncSelectOption("cap-cierre-empresa", data.empresa_capacitadora);
        document.getElementById("cap-cierre-empresa-quick-nombre").value = "";
        togglePanel("cap-cierre-empresa-quick", false);
      } catch (err) {
        alert(err.message);
      }
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
      const fechaReal = document.getElementById("cap-cierre-fecha")?.value || "";
      if (!fechaReal) {
        alert("Indicá la fecha de realización del curso");
        return;
      }
      const empresaId = document.getElementById("cap-cierre-empresa")?.value || "";
      if (asistenciaEsExterno && !empresaId) {
        alert("Seleccioná la empresa externa que dictó el curso");
        return;
      }
      const payload = {
        personas: registros,
        fecha_realizacion: fechaReal,
        capacitador: document.getElementById("cap-cierre-capacitador")?.value || null,
        lugar: document.getElementById("cap-cierre-lugar")?.value || null,
        link: document.getElementById("cap-cierre-link")?.value || null,
      };
      if (asistenciaEsExterno) {
        payload.empresa_capacitadora_id = Number(empresaId);
      }
      try {
        const matFile = document.getElementById("cap-cierre-material")?.files?.[0];
        const resFile = document.getElementById("cap-cierre-resultados")?.files?.[0];
        if (matFile) await uploadFile(`${API}/encuentros/${asistenciaEncuentroId}/material`, matFile);
        if (resFile) await uploadFile(`${API}/encuentros/${asistenciaEncuentroId}/resultados`, resFile);
        await putJson(`${API}/encuentros/${asistenciaEncuentroId}/cierre`, payload);
        closeAsistenciaModal();
        if (typeof loadEncuentros === "function") await loadEncuentros(true);
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



  function openSectorForm(item) {

    const form = document.getElementById("cap-sector-form");

    if (!form) return;

    form.reset();

    document.getElementById("cap-s-id").value = item?.id || "";

    document.getElementById("cap-s-codigo").value = item?.codigo || "";

    document.getElementById("cap-s-nombre").value = item?.nombre || "";

    setFormError("cap-sector-form-error", "");

    togglePanel("cap-sector-form-panel", true);

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

          const resolution = await resolveSimilarBeforeCreate({

            tipo: "sector",

            nombre: payload.nombre,

            codigo: payload.codigo,

          });

          if (resolution.action === "cancel") return;

          if (resolution.action === "use") {

            togglePanel("cap-sector-form-panel", false);

            form.reset();

            await loadSectores();

            metaSectores = (await fetchJson(`${API}/sectores`)).sectores || [];

            fillSelect("cap-p-sector", metaSectores, "— Sin sector —");

            return;

          }

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



  function bindClienteForm() {
    const form = document.getElementById("cap-cliente-form");
    if (!form) return;
    document.getElementById("cap-btn-nuevo-cliente")?.addEventListener("click", () => {
      clienteEditId = null;
      form.reset();
      document.getElementById("cap-cli-id").value = "";
      document.getElementById("cap-cliente-baja")?.classList.add("cap-hidden");
      setFormError("cap-cliente-form-error", "");
      togglePanel("cap-cliente-form-panel", true);
      document.getElementById("cap-cli-nombre")?.focus();
    });
    document.getElementById("cap-cliente-cancel")?.addEventListener("click", () => {
      clienteEditId = null;
      togglePanel("cap-cliente-form-panel", false);
    });
    document.getElementById("cap-cliente-baja")?.addEventListener("click", async () => {
      if (!clienteEditId) return;
      if (!confirm("¿Dar de baja este cliente?")) return;
      try {
        await deleteJson(`${API}/clientes/${clienteEditId}`);
        clienteEditId = null;
        togglePanel("cap-cliente-form-panel", false);
        await loadClientes();
      } catch (err) {
        setFormError("cap-cliente-form-error", err.message);
      }
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        codigo: document.getElementById("cap-cli-codigo")?.value.trim(),
        nombre: document.getElementById("cap-cli-nombre")?.value.trim(),
      };
      try {
        if (clienteEditId) {
          await putJson(`${API}/clientes/${clienteEditId}`, payload);
        } else {
          await postJson(`${API}/clientes`, payload);
        }
        clienteEditId = null;
        togglePanel("cap-cliente-form-panel", false);
        form.reset();
        await loadClientes();
      } catch (err) {
        setFormError("cap-cliente-form-error", err.message);
      }
    });
    document.getElementById("cap-cliente-logo-file")?.addEventListener("change", async (ev) => {
      const file = ev.target.files?.[0];
      ev.target.value = "";
      if (!file || !clienteLogoId) return;
      try {
        await uploadFile(`${API}/clientes/${clienteLogoId}/logo`, file);
        await loadClientes();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  async function loadClientes() {
    const tbody = document.getElementById("cap-clientes-body");
    if (!tbody) return;
    try {
      const data = await fetchJson(`${API}/clientes`);
      metaClientes = data.clientes || [];
    tbody.innerHTML = metaClientes.map((c) => {
      const logo = c.tiene_logo
        ? `<img class="cap-table-logo" src="${API}/clientes/${c.id}/logo?t=${Date.now()}" alt="" onerror="this.replaceWith(document.createTextNode('—'))">`
        : '<span class="cap-muted">—</span>';
      return `<tr data-id="${c.id}">
        <td>${logo}</td>
        <td>${escapeHtml(c.codigo || "")}</td>
        <td>${escapeHtml(c.nombre)}</td>
        <td>${c.personas_count || 0}</td>
        <td class="cap-col-actions">
          <button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" data-cli-logo="${c.id}" title="Logo"><i class="bi bi-image"></i></button>
          <button type="button" class="cap-btn cap-btn--ghost cap-btn--xs" data-cli-edit="${c.id}" title="Editar"><i class="bi bi-pencil"></i></button>
        </td>
      </tr>`;
    }).join("") || '<tr><td colspan="5" class="cap-empty">Sin clientes. Agregá las empresas a las que afecta el personal.</td></tr>';
    tbody.querySelectorAll("[data-cli-edit]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const c = metaClientes.find((x) => String(x.id) === btn.dataset.cliEdit);
        if (!c) return;
        clienteEditId = c.id;
        document.getElementById("cap-cli-id").value = c.id;
        document.getElementById("cap-cli-codigo").value = c.codigo || "";
        document.getElementById("cap-cli-nombre").value = c.nombre || "";
        document.getElementById("cap-cliente-baja")?.classList.remove("cap-hidden");
        setFormError("cap-cliente-form-error", "");
        togglePanel("cap-cliente-form-panel", true);
      });
    });
    tbody.querySelectorAll("[data-cli-logo]").forEach((btn) => {
      btn.addEventListener("click", () => {
        clienteLogoId = Number(btn.dataset.cliLogo);
        document.getElementById("cap-cliente-logo-file")?.click();
      });
    });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" class="cap-empty">${escapeHtml(err.message)}</td></tr>`;
    }
  }

  function bindInformes() {
    document.getElementById("cap-informe-volver")?.addEventListener("click", () => {
      document.getElementById("cap-informe-doc")?.classList.add("cap-hidden");
      document.getElementById("cap-informes-list")?.classList.remove("cap-hidden");
    });
    document.getElementById("cap-informe-imprimir")?.addEventListener("click", () => window.print());
  }

  async function loadInformesList() {
    const wrap = document.getElementById("cap-informes-cards");
    if (!wrap) return;
    const data = await fetchJson(`${API}/clientes`);
    const clientes = data.clientes || [];
    if (!clientes.length) {
      wrap.innerHTML = '<p class="cap-empty">Todavía no hay clientes. Crealos en Cursos y catálogos y asigná personas a cada empresa.</p>';
      return;
    }
    wrap.innerHTML = clientes.map((c) => {
      const logo = c.tiene_logo
        ? `<img src="${API}/clientes/${c.id}/logo?t=${Date.now()}" alt="">`
        : `<span class="cap-cliente-card__ph">${escapeHtml((c.nombre || "?").slice(0, 2).toUpperCase())}</span>`;
      return `<button type="button" class="cap-cliente-card" data-cliente-id="${c.id}">
        <span class="cap-cliente-card__logo">${logo}</span>
        <span class="cap-cliente-card__name">${escapeHtml(c.nombre)}</span>
        <span class="cap-cliente-card__meta">${c.personas_count || 0} persona${(c.personas_count || 0) === 1 ? "" : "s"}</span>
      </button>`;
    }).join("");
    wrap.querySelectorAll("[data-cliente-id]").forEach((btn) => {
      btn.addEventListener("click", () => loadInformeCliente(Number(btn.dataset.clienteId)).catch(console.error));
    });
  }

  async function loadInformeCliente(clienteId) {
    const data = await fetchJson(`${API}/clientes/${clienteId}/informe`);
    document.getElementById("cap-informes-list")?.classList.add("cap-hidden");
    document.getElementById("cap-informe-doc")?.classList.remove("cap-hidden");
    const cli = data.cliente || {};
    document.getElementById("cap-informe-cliente-nombre").textContent = cli.nombre || "Cliente";
    const fecha = data.fecha_informe ? data.fecha_informe.split("-").reverse().join("/") : "";
    document.getElementById("cap-informe-fecha").textContent = fecha ? `Fecha del informe: ${fecha}` : "";

    const logoEmp = document.getElementById("cap-informe-logo-empresa");
    if (logoEmp) {
      const emp = data.logo_empresa || {};
      logoEmp.onerror = () => { logoEmp.src = emp.fallback_url || "/static/img/gos-logo.png"; };
      logoEmp.src = emp.tiene_logo ? `${emp.url}?t=${Date.now()}` : (emp.fallback_url || "/static/img/gos-logo.png");
    }
    const logoCli = document.getElementById("cap-informe-logo-cliente");
    const ph = document.getElementById("cap-informe-logo-cliente-ph");
    if (logoCli && ph) {
      if (cli.tiene_logo) {
        logoCli.src = `${API}/clientes/${cli.id}/logo?t=${Date.now()}`;
        logoCli.classList.remove("cap-hidden");
        ph.classList.add("cap-hidden");
      } else {
        logoCli.classList.add("cap-hidden");
        ph.textContent = (cli.nombre || "C").slice(0, 1).toUpperCase();
        ph.classList.remove("cap-hidden");
      }
    }

    const k = data.kpis || {};
    const kpis = document.getElementById("cap-informe-kpis");
    if (kpis) {
      kpis.innerHTML = [
        ["Personas", k.personas_activas],
        ["Cumplimiento", `${k.cumplimiento_general || 0}%`],
        ["Pendientes", k.pendientes],
        ["Vencidas", k.vencidas],
        ["Horas (mes)", k.horas_hombre_mes],
        ["Aprobación", `${k.tasa_aprobacion || 0}%`],
      ].map(([label, val]) => `
        <div class="cap-kpi-card"><span class="cap-kpi-label">${label}</span><span class="cap-kpi-value">${val ?? "—"}</span></div>
      `).join("");
    }

    const hab = document.getElementById("cap-informe-hab");
    const inh = document.getElementById("cap-informe-inh");
    if (hab) hab.textContent = `${data.habilitados_pct || 0}%`;
    if (inh) inh.textContent = `${data.inhabilitados_pct || 0}%`;

    const tbody = document.getElementById("cap-informe-personas-body");
    const personas = data.personas_detalle || [];
    if (tbody) {
      tbody.innerHTML = personas.map((p) => `
        <tr>
          <td>${escapeHtml(p.nombre)}</td>
          <td>${escapeHtml(p.legajo || "—")}</td>
          <td>${escapeHtml(p.puesto || "—")}</td>
          <td>${p.habilitada ? '<span class="cap-badge cap-badge--green">Habilitado</span>' : '<span class="cap-badge cap-badge--red">No habilitado</span>'}</td>
          <td>${p.pct}%</td>
          <td>${p.pendientes}</td>
        </tr>
      `).join("") || '<tr><td colspan="6" class="cap-empty">Ninguna persona asignada a este cliente.</td></tr>';
    }

    const sect = document.getElementById("cap-informe-sectores");
    if (sect) {
      sect.innerHTML = (data.cumplimiento_por_sector || []).map((s) => `
        <div class="cap-bar-row">
          <span class="cap-bar-label">${escapeHtml(s.nombre)}</span>
          <div class="cap-bar-track"><div class="cap-bar-fill" style="width:${s.pct}%"></div></div>
          <span class="cap-bar-pct">${s.pct}%</span>
        </div>`).join("") || "<p class='cap-empty'>Sin datos</p>";
    }
    const evo = document.getElementById("cap-informe-evolucion");
    if (evo) {
      const items = data.evolucion_mensual || [];
      const max = Math.max(...items.map((i) => i.realizadas), 1);
      evo.innerHTML = `<div class="cap-vbars">${items.map((i) => `
        <div class="cap-bar-row cap-bar-row--vertical">
          <div class="cap-vbar" style="height:${Math.round(i.realizadas / max * 100)}%" title="${i.realizadas}"></div>
          <span class="cap-bar-label">${(i.mes || "").slice(5)}</span>
        </div>`).join("")}</div>`;
    }

    const canvas = document.getElementById("cap-informe-donut");
    const personal = (data.recursos || []).find((r) => r.clave === "personal");
    if (canvas && typeof Chart !== "undefined" && personal) {
      if (chartInforme) chartInforme.destroy();
      chartInforme = new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: ["Habilitados", "No habilitados"],
          datasets: [{ data: [personal.verde, personal.rojo], backgroundColor: ["#76B947", "#e74c3c"] }],
        },
        options: { plugins: { legend: { position: "bottom" } }, maintainAspectRatio: false },
      });
    }
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

    bindSimilarModal();

    bindPersonaForm();

    bindCursoForm();
    bindCursoCascada();
    bindTaxonomiaForm();
    await ensureTaxonomia();

    bindSectorForm();

    bindClienteForm();
    bindInformes();

    bindMatriz();
    bindCronogramaResumen();

    bindAlertas();

    bindConfig();

    bindGlobalSearch();

    bindPersonasFilters();

    bindReportes();

    bindCertUpload();

    bindFotoUpload();

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
      try { await Promise.all([loadEncuentros(), loadPuestosOptions()]); } catch (e) { console.error(e); }
    }

    if (view === "programas") {

      try { await loadCursos(); } catch (e) { console.error(e); }

      try { await loadPuestosOptions(); } catch (e) { console.error(e); }

      try { await loadProgPlanCatalog(); } catch (e) { console.error(e); }

      try { await loadProgramas(); } catch (e) { console.error(e); }

      if (!programasCache.length) {
        try { await abrirFormularioPrograma(); } catch (e) { console.error(e); }
      }

    }

    if (view === "matriz") {
      try {
        await initMatrizAnalitica();
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

    if (view === "informes") {
      try { await loadInformesList(); } catch (e) { console.error(e); }
    }

    if (view === "catalogos") {

      try { await loadCursos(); } catch (e) { console.error(e); }

      try { await loadSectores(); } catch (e) { console.error(e); }

      try { await loadClientes(); } catch (e) { console.error(e); }

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



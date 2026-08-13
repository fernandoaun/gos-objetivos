(function () {
  const btn = document.getElementById("btnPresentacionModulo");
  const modalEl = document.getElementById("modalPresentacionGos");
  if (!btn || !modalEl || typeof bootstrap === "undefined") return;

  const listEl = document.getElementById("presentacionSubmodulosList");
  const errEl = document.getElementById("presentacionError");
  const sistemaEl = document.getElementById("presentacionSistemaLabel");
  const titleEl = document.getElementById("modalPresentacionGosLabel");
  const genBtn = document.getElementById("presentacionGenerarBtn");
  const selectAllBtn = document.getElementById("presentacionSelectAll");
  const selectNoneBtn = document.getElementById("presentacionSelectNone");
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  const catalogEl = document.getElementById("presentacionCatalogData");

  let catalog = null;
  let currentModule = btn.getAttribute("data-module") || "";

  function showError(msg) {
    if (!errEl) return;
    errEl.textContent = msg || "";
    errEl.classList.toggle("d-none", !msg);
  }

  function setChecks(checked) {
    listEl.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = checked;
    });
  }

  function selectedCodes() {
    return Array.from(listEl.querySelectorAll('input[type="checkbox"]:checked')).map(
      (el) => el.value
    );
  }

  function renderSubmodulos(mod) {
    listEl.innerHTML = "";
    (mod.submodulos || []).forEach((sub) => {
      const id = `pres-sub-${mod.code}-${sub.code}`;
      const label = document.createElement("label");
      label.className = "pe-presentacion-check";
      label.setAttribute("for", id);
      label.innerHTML =
        `<input type="checkbox" id="${id}" value="${sub.code}" checked>` +
        `<span>${sub.label}</span>`;
      listEl.appendChild(label);
    });
  }

  function readEmbeddedCatalog() {
    if (!catalogEl || !catalogEl.textContent) return null;
    try {
      const data = JSON.parse(catalogEl.textContent);
      return Array.isArray(data) ? data : null;
    } catch (_err) {
      return null;
    }
  }

  async function loadCatalog() {
    if (catalog) return catalog;
    const embedded = readEmbeddedCatalog();
    if (embedded && embedded.length) {
      catalog = embedded;
      return catalog;
    }
    const res = await fetch("/api/presentacion/catalogo", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!res.ok) {
      throw new Error(
        "No se pudo cargar el catálogo. Reiniciá el servidor local para cargar la ruta nueva."
      );
    }
    const data = await res.json();
    catalog = data.modulos || [];
    return catalog;
  }

  async function openModal() {
    showError("");
    try {
      const mods = await loadCatalog();
      const mod = mods.find((m) => m.code === currentModule);
      if (!mod) {
        showError("Este módulo no tiene presentación disponible.");
        modal.show();
        return;
      }
      titleEl.textContent = `Presentación · ${mod.label}`;
      sistemaEl.textContent = mod.sistema || "";
      renderSubmodulos(mod);
      modal.show();
    } catch (err) {
      showError(err.message || "Error al abrir la presentación.");
      modal.show();
    }
  }

  async function downloadPptx() {
    showError("");
    const subs = selectedCodes();
    if (!subs.length) {
      showError("Elegí al menos un submódulo.");
      return;
    }
    genBtn.disabled = true;
    const original = genBtn.innerHTML;
    genBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Generando…';
    try {
      const res = await fetch("/api/presentacion/generar", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json, application/octet-stream",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ module: currentModule, submodulos: subs }),
      });
      const ctype = res.headers.get("Content-Type") || "";
      if (!res.ok) {
        let msg = "No se pudo generar la presentación.";
        if (res.status === 404) {
          msg = "Falta reiniciar el servidor local para activar la generación PPTX.";
        } else if (ctype.includes("application/json")) {
          const data = await res.json();
          msg = data.error || msg;
        }
        throw new Error(msg);
      }
      const blob = await res.blob();
      let filename = "Presentacion_GOS.pptx";
      const cd = res.headers.get("Content-Disposition") || "";
      const match = /filename\*?=(?:UTF-8''|")?([^\";]+)/i.exec(cd);
      if (match) {
        filename = decodeURIComponent(match[1].replace(/"/g, "").trim());
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      modal.hide();
    } catch (err) {
      showError(err.message || "Error al descargar.");
    } finally {
      genBtn.disabled = false;
      genBtn.innerHTML = original;
    }
  }

  btn.addEventListener("click", openModal);
  genBtn.addEventListener("click", downloadPptx);
  selectAllBtn.addEventListener("click", () => setChecks(true));
  selectNoneBtn.addEventListener("click", () => setChecks(false));
})();

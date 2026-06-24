document.addEventListener("DOMContentLoaded", function () {
  var input = document.querySelector('.foda-file-btn input[type="file"]');
  var label = document.getElementById("fodaDropzone");
  var fileName = document.getElementById("fodaFileName");

  if (input && label) {
    input.addEventListener("change", function () {
      if (fileName && input.files[0]) {
        fileName.textContent = input.files[0].name;
      } else if (fileName) {
        fileName.textContent = "";
      }
    });

    ["dragenter", "dragover"].forEach(function (ev) {
      label.addEventListener(ev, function (e) {
        e.preventDefault();
        label.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(function (ev) {
      label.addEventListener(ev, function (e) {
        e.preventDefault();
        label.classList.remove("dragover");
      });
    });

    label.addEventListener("drop", function (e) {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
      }
    });
  }

  var saveUrl = document.body.getAttribute("data-dafo-save-url");
  if (!saveUrl) return;

  document.querySelectorAll(".dafo-tarea-block").forEach(function (block) {
    var view = block.querySelector(".dafo-tarea-view");
    var edit = block.querySelector(".dafo-tarea-edit");
    var textEl = block.querySelector(".dafo-tarea-text");
    var ta = block.querySelector(".dafo-tarea-input");
    var editBtn = block.querySelector(".dafo-tarea-edit-btn");
    var cancelBtn = block.querySelector(".dafo-tarea-cancel-btn");
    var status = block.querySelector(".dafo-save-status");
    if (!view || !edit || !textEl || !ta || !editBtn) return;

    var saved = ta.value;
    var saving = false;

    function setStatus(text, ok) {
      if (!status) return;
      status.textContent = text;
      status.className = "dafo-save-status" + (ok ? " is-ok" : text ? " is-err" : "");
    }

    function updateViewText(value) {
      var trimmed = (value || "").trim();
      textEl.textContent = trimmed || "Sin tarea definida.";
      textEl.classList.toggle("is-empty", !trimmed);
    }

    function showView() {
      view.classList.remove("d-none");
      edit.classList.add("d-none");
      setStatus("", true);
    }

    function showEdit() {
      ta.value = saved;
      view.classList.add("d-none");
      edit.classList.remove("d-none");
      ta.focus();
    }

    function saveTarea() {
      if (saving) return Promise.resolve();
      if (ta.value === saved) {
        showView();
        return Promise.resolve();
      }
      saving = true;
      setStatus("Guardando…", true);
      return fetch(saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({
          tipo: ta.dataset.tipo,
          tarea: ta.value,
        }),
      })
        .then(function (r) {
          return r.json().then(function (data) {
            if (!r.ok) throw new Error(data.error || "Error al guardar");
            return data;
          });
        })
        .then(function () {
          saved = ta.value;
          updateViewText(saved);
          showView();
          setStatus("Guardado", true);
          window.setTimeout(function () {
            setStatus("", true);
          }, 2000);
        })
        .catch(function (err) {
          setStatus(err.message || "Error", false);
        })
        .finally(function () {
          saving = false;
        });
    }

    editBtn.addEventListener("click", showEdit);

    if (cancelBtn) {
      cancelBtn.addEventListener("mousedown", function (e) {
        e.preventDefault();
      });
      cancelBtn.addEventListener("click", function () {
        ta.value = saved;
        showView();
      });
    }

    ta.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        e.preventDefault();
        ta.value = saved;
        showView();
      }
    });

    ta.addEventListener("blur", function () {
      window.setTimeout(function () {
        if (edit.classList.contains("d-none")) return;
        if (edit.contains(document.activeElement)) return;
        saveTarea();
      }, 0);
    });
  });
});

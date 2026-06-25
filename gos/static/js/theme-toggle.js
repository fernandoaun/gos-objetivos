(function () {
  const KEY = "gos-theme";
  const root = document.documentElement;
  const saved = localStorage.getItem(KEY);
  if (saved) root.setAttribute("data-theme", saved);

  document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("themeToggle");
    const icon = document.getElementById("themeIcon");
    if (!btn) return;

    function syncIcon() {
      const dark = root.getAttribute("data-theme") === "dark";
      if (icon) {
        icon.className = dark ? "bi bi-sun" : "bi bi-moon-stars";
      }
    }
    syncIcon();

    btn.addEventListener("click", function () {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem(KEY, next);
      syncIcon();
      document.querySelectorAll("iframe").forEach(function (frame) {
        try {
          frame.contentWindow.postMessage({ type: "gos-theme", theme: next }, "*");
        } catch (_) { /* iframe no listo */ }
      });
    });
  });
})();

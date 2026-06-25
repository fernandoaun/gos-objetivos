(function () {
  var KEY = "gos-theme";
  var root = document.documentElement;
  var saved = localStorage.getItem(KEY);
  if (saved) root.setAttribute("data-theme", saved);

  window.addEventListener("message", function (e) {
    if (e.data && e.data.type === "gos-theme") {
      root.setAttribute("data-theme", e.data.theme);
      localStorage.setItem(KEY, e.data.theme);
    }
  });
})();

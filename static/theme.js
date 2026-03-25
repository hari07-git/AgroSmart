(() => {
  const KEY = "agrosmart:theme";

  function preferredTheme() {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
    try {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    } catch {
      return "light";
    }
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }

  function toggle() {
    const cur = document.documentElement.getAttribute("data-theme") || preferredTheme();
    const next = cur === "dark" ? "light" : "dark";
    localStorage.setItem(KEY, next);
    apply(next);
  }

  apply(preferredTheme());

  const btn = document.querySelector("[data-theme-toggle]");
  if (btn) btn.addEventListener("click", toggle);
})();


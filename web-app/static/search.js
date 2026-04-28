(() => {
  const input = document.getElementById("prof-search");
  const resultsEl = document.getElementById("prof-search-results");
  if (!input || !resultsEl) return;

  let debounceTimer = null;
  let abortController = null;

  function hideResults() {
    resultsEl.hidden = true;
    resultsEl.innerHTML = "";
  }

  function escapeHtml(value) {
    return (value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function render(results) {
    if (!results || results.length === 0) {
      resultsEl.innerHTML = '<div class="nav-search-empty">No matches</div>';
      resultsEl.hidden = false;
      return;
    }

    resultsEl.innerHTML = results
      .map((p) => {
        const id = encodeURIComponent(p.id || "");
        const name = escapeHtml(p.name);
        const title = escapeHtml(p.title);
        const email = escapeHtml(p.email);
        return `
          <a class="nav-search-item" href="/professors/${id}">
            <div class="nav-search-name">${name}</div>
            ${title ? `<div class="nav-search-sub">${title}</div>` : ""}
            ${email ? `<div class="nav-search-sub">Email: ${email}</div>` : ""}
          </a>
        `;
      })
      .join("");
    resultsEl.hidden = false;
  }

  async function doSearch(value) {
    if (abortController) abortController.abort();
    abortController = new AbortController();

    const q = value.trim();
    if (!q) return hideResults();

    const resp = await fetch(`/api/professors/search?q=${encodeURIComponent(q)}`, {
      signal: abortController.signal,
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) return;
    const data = await resp.json();
    render(data.results || []);
  }

  input.addEventListener("input", () => {
    const value = input.value;
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => doSearch(value).catch(() => {}), 150);
  });

  input.addEventListener("focus", () => {
    if (input.value.trim()) doSearch(input.value).catch(() => {});
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      input.value = "";
      hideResults();
      input.blur();
    }
  });

  document.addEventListener("click", (e) => {
    if (!resultsEl.contains(e.target) && e.target !== input) hideResults();
  });
})();

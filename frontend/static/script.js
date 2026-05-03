document.addEventListener("DOMContentLoaded", () => {
  const firstFavoriteInput = document.querySelector("#favorite_1");
  if (firstFavoriteInput) firstFavoriteInput.focus();

  // ── Watchlist toggle with toast undo ─────────────────────────────────────

  let toastEl = null;
  let toastTimer = null;

  function buildToast() {
    const el = document.createElement("div");
    el.className = "toast";
    el.innerHTML =
      '<span class="toast-msg"></span>' +
      '<button class="toast-undo" type="button">Undo</button>';
    document.body.appendChild(el);
    return el;
  }

  function showToast(message, onUndo) {
    if (!toastEl) toastEl = buildToast();
    clearTimeout(toastTimer);

    toastEl.querySelector(".toast-msg").textContent = message;

    // Swap undo button node to drop any previous click listener
    const oldBtn = toastEl.querySelector(".toast-undo");
    const newBtn = oldBtn.cloneNode(true);
    oldBtn.replaceWith(newBtn);
    newBtn.addEventListener("click", () => { onUndo(); hideToast(); });

    requestAnimationFrame(() => toastEl.classList.add("visible"));
    toastTimer = setTimeout(hideToast, 4000);
  }

  function hideToast() {
    clearTimeout(toastTimer);
    toastEl?.classList.remove("visible");
  }

  // Reset loading buttons when the page is restored from bfcache
  window.addEventListener("pageshow", () => {
    for (const btn of document.querySelectorAll("button[data-loading]")) {
      btn.textContent = btn.dataset.originalText || btn.textContent;
      btn.disabled = false;
      btn.removeAttribute("data-loading");
      btn.removeAttribute("data-original-text");
    }
  });

  document.addEventListener("submit", (e) => {
    const form = e.target;

    // ── Page-navigating forms: show loading state on the submit button ────────
    if (!form.action?.includes("/watchlist/toggle/")) {
      const btn = form.querySelector("button");
      if (btn && !btn.hasAttribute("data-loading")) {
        btn.dataset.originalText = btn.textContent.trim();
        btn.disabled = true;
        btn.dataset.loading = "";
        btn.textContent = form.action?.includes("/recommendations")
          ? "Generating…"
          : "Searching…";
      }
      return;
    }

    e.preventDefault();

    const btn = form.querySelector("button");
    const originalText = btn.textContent.trim();
    const isRemoving = originalText.startsWith("Remove");

    fetch(form.action, {
      method: "POST",
      redirect: "manual",
      body: new FormData(form),
    });

    if (isRemoving) {
      btn.textContent = "Add to Watchlist";

      // Dim the card only when it lives inside the watchlist page list
      const card = form.closest("li.movie-card");
      const inWatchlist = card?.closest(".favorites-section");

      if (inWatchlist) {
        card.style.transition = "opacity 0.2s";
        card.style.opacity = "0.35";
      }

      let undone = false;

      showToast("Removed from watchlist", () => {
        undone = true;
        fetch(form.action, { method: "POST", redirect: "manual", body: new FormData(form) });
        btn.textContent = originalText;
        if (inWatchlist) card.style.opacity = "";
      });

      // Remove card from DOM after undo window closes (watchlist page only)
      setTimeout(() => {
        if (!undone && inWatchlist) card.remove();
      }, 4200);
    } else {
      btn.textContent = "Remove from Watchlist";
    }
  });
});

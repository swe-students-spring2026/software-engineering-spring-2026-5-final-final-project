(() => {
  const hash = window.location.hash;
  if (!hash || !hash.startsWith("#post-")) return;

  const target = document.querySelector(hash);
  if (!target) return;

  // Let the browser perform its normal anchor jump first, then recenter.
  requestAnimationFrame(() => {
    try {
      target.scrollIntoView({ block: "center" });
    } catch (_err) {
      target.scrollIntoView();
    }
  });
})();


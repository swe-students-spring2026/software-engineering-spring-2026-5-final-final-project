/**
 * Placeholder client-side script.
 *
 * Currently handles:
 *   - Clearing the search input when the user focuses it (UX nicety)
 *
 * TODO: wire up live search preview, favorites toggling, etc.
 */

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.querySelector(".search-input");
  if (searchInput) {
    searchInput.addEventListener("focus", () => {
      // Placeholder: could trigger a live-preview dropdown here
    });
  }
});

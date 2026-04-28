(() => {
  const tickers = document.querySelectorAll(".ticker");
  if (!tickers.length) return;

  function updateTicker(ticker) {
    const content = ticker.querySelector(".ticker-content");
    if (!content) return;

    const hasOverflow = content.scrollWidth > ticker.clientWidth + 2;
    ticker.classList.toggle("is-scrollable", hasOverflow);
  }

  function updateAll() {
    tickers.forEach(updateTicker);
  }

  window.addEventListener("resize", updateAll);
  updateAll();
})();


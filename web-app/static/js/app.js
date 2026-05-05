// Moodify front-end interactions

(function () {
  "use strict";

  // ── slider live values ──
  const energySlider = document.getElementById("energy-slider");
  const valenceSlider = document.getElementById("valence-slider");
  const energyVal = document.getElementById("energy-val");
  const valenceVal = document.getElementById("valence-val");

  // turn the energy + valence pair into a short readable mood label
  function describeSliders(energy, valence) {
    const e = parseInt(energy, 10);
    const v = parseInt(valence, 10);
    const energyLabel = e >= 75 ? "energetic" : e <= 25 ? "mellow" : "moderate";
    const valenceLabel = v >= 75 ? "upbeat" : v <= 25 ? "somber" : "neutral";
    return `feeling ${energyLabel} and ${valenceLabel}`;
  }

  function onSliderChange() {
    if (energyVal) energyVal.textContent = energySlider ? energySlider.value : "";
    if (valenceVal) valenceVal.textContent = valenceSlider ? valenceSlider.value : "";

    // user is in custom mode now — clear any active emoji
    document.querySelectorAll(".emoji-btn.active").forEach((b) => b.classList.remove("active"));
    if (moodLabelInput) moodLabelInput.value = "";

    // refresh the textarea hint if the user hasn't typed their own
    if (moodTextarea && textareaIsEmojiOwned && energySlider && valenceSlider) {
      moodTextarea.value = describeSliders(energySlider.value, valenceSlider.value);
    }
  }

  if (energySlider) energySlider.addEventListener("input", onSliderChange);
  if (valenceSlider) valenceSlider.addEventListener("input", onSliderChange);

  // ── emoji mood buttons ──
  const moodLabelInput = document.getElementById("mood-label");
  const moodTextarea = document.getElementById("mood-text");

  // track whether the textarea text came from emoji clicks (vs. user typing)
  // start true if textarea is empty so the first click always fills it
  let textareaIsEmojiOwned = !moodTextarea || !moodTextarea.value.trim();

  // user typing flips ownership back to "manual" and we won't overwrite
  if (moodTextarea) {
    moodTextarea.addEventListener("input", () => {
      textareaIsEmojiOwned = false;
    });
  }

  document.querySelectorAll(".emoji-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".emoji-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      if (energySlider && btn.dataset.energy) {
        energySlider.value = btn.dataset.energy;
        if (energyVal) energyVal.textContent = btn.dataset.energy;
      }
      if (valenceSlider && btn.dataset.valence) {
        valenceSlider.value = btn.dataset.valence;
        if (valenceVal) valenceVal.textContent = btn.dataset.valence;
      }
      if (moodLabelInput) moodLabelInput.value = btn.dataset.mood || "";

      // overwrite the textarea on every emoji click as long as the user
      // hasn't typed their own description
      if (moodTextarea && textareaIsEmojiOwned) {
        moodTextarea.value = btn.textContent.trim();
      }
    });
  });

  // restore active emoji when re-rendered after POST
  const savedMoodEl = document.getElementById("saved-mood-label");
  if (savedMoodEl && savedMoodEl.value) {
    const btn = document.querySelector(`.emoji-btn[data-mood="${savedMoodEl.value}"]`);
    if (btn) btn.classList.add("active");
  }

  // ── city selector ──
  const citiesData = document.getElementById("cities-data");
  const citySearch = document.getElementById("city-search");
  const cityDropdown = document.getElementById("city-dropdown");
  const cityLat = document.getElementById("city-lat");
  const cityLon = document.getElementById("city-lon");
  const cityNameHidden = document.getElementById("city-name-hidden");

  if (citiesData && citySearch && cityDropdown) {
    let CITIES = [];
    try {
      CITIES = JSON.parse(citiesData.textContent);
    } catch (e) {
      CITIES = [];
    }

    let currentFiltered = [];
    let highlightedIdx = -1;

    function renderDropdown(query) {
      const q = query.trim().toLowerCase();
      currentFiltered = q
        ? CITIES.filter(
            (c) =>
              c.name.toLowerCase().includes(q) ||
              c.state.toLowerCase().includes(q)
          )
        : CITIES;
      highlightedIdx = -1;
      cityDropdown.innerHTML = "";
      if (!currentFiltered.length) {
        cityDropdown.innerHTML = '<div class="city-no-results">No cities found</div>';
        return;
      }
      currentFiltered.slice(0, 50).forEach((city) => {
        const div = document.createElement("div");
        div.className = "city-option";
        div.setAttribute("role", "option");
        const name = document.createElement("span");
        name.textContent = city.name;
        const state = document.createElement("span");
        state.className = "city-opt-state";
        state.textContent = city.state;
        div.append(name, state);
        div.addEventListener("mousedown", (ev) => {
          ev.preventDefault();
          selectCity(city);
        });
        cityDropdown.appendChild(div);
      });
    }

    function selectCity(city) {
      const label = `${city.name}, ${city.state}`;
      citySearch.value = label;
      if (cityLat) cityLat.value = city.lat;
      if (cityLon) cityLon.value = city.lon;
      if (cityNameHidden) cityNameHidden.value = label;
      cityDropdown.classList.remove("open");
    }

    function updateHighlight() {
      cityDropdown.querySelectorAll(".city-option").forEach((el, i) =>
        el.classList.toggle("highlighted", i === highlightedIdx)
      );
      const hl = cityDropdown.querySelector(".city-option.highlighted");
      if (hl) hl.scrollIntoView({ block: "nearest" });
    }

    citySearch.addEventListener("focus", () => {
      renderDropdown(citySearch.value);
      cityDropdown.classList.add("open");
    });
    citySearch.addEventListener("input", () => {
      renderDropdown(citySearch.value);
      cityDropdown.classList.add("open");
    });
    citySearch.addEventListener("blur", () => cityDropdown.classList.remove("open"));
    citySearch.addEventListener("keydown", (ev) => {
      const opts = cityDropdown.querySelectorAll(".city-option");
      if (ev.key === "ArrowDown") {
        ev.preventDefault();
        highlightedIdx = Math.min(highlightedIdx + 1, opts.length - 1);
        updateHighlight();
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        highlightedIdx = Math.max(highlightedIdx - 1, 0);
        updateHighlight();
      } else if (ev.key === "Enter" && highlightedIdx >= 0) {
        ev.preventDefault();
        selectCity(currentFiltered[highlightedIdx]);
      } else if (ev.key === "Escape") {
        cityDropdown.classList.remove("open");
      }
    });
  }

  // ── time of day ──
  const timeLabel = document.getElementById("time-label");
  const timeSub = document.getElementById("time-sub");
  if (timeLabel && timeSub) {
    const hour = new Date().getHours();
    if (hour < 6) {
      timeLabel.textContent = "Late night";
      timeSub.textContent = "quiet & reflective";
    } else if (hour < 12) {
      timeLabel.textContent = "Morning";
      timeSub.textContent = "boosts energy";
    } else if (hour < 17) {
      timeLabel.textContent = "Afternoon";
      timeSub.textContent = "upbeat vibes";
    } else if (hour < 21) {
      timeLabel.textContent = "Evening";
      timeSub.textContent = "wind-down mode";
    } else {
      timeLabel.textContent = "Night";
      timeSub.textContent = "chill & mellow";
    }
  }

  // ── loading state on form submit ──
  const moodForm = document.getElementById("mood-form");
  const submitBtn = document.getElementById("submit-btn");
  if (moodForm && submitBtn) {
    moodForm.addEventListener("submit", () => {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Finding tracks...';
    });
  }

  // ── auto-dismiss flash messages after 5s ──
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
})();

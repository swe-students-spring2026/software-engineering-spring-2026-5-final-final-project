const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const HOUR_START = 8, HOUR_END = 22;
const PX_PER_HOUR = 48;
const COLORS = ["#7c3aed", "#0369a1", "#065f46", "#92400e", "#9f1239", "#1d4ed8", "#b45309", "#0f766e"];
let colorIdx = 0;

let schedule = JSON.parse(localStorage.getItem("nyu_schedule") || "[]");
function saveSchedule() { localStorage.setItem("nyu_schedule", JSON.stringify(schedule)); }

let pendingLecture = null, pendingRcts = [], selectedRct = null;
const sectionMap = {};

function getMeetingSlots(section) {
    return (section?.meeting_times || [])
        .filter(t => t.start && t.end && typeof t.day_num === "number")
        .map(t => ({ dayIdx: t.day_num, start: t.start, end: t.end }));
}

function timeToFrac(t) {
    const [h, m] = t.split(':').map(Number);
    return h + m / 60;
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function topicText(section) {
  return String(section?.topic || "").trim();
}

// ── Calendar collapse ──
let calCollapsed = false;
function toggleCalendar() {
    calCollapsed = !calCollapsed;
    const panel = document.getElementById('cal-panel');
    const btn = document.getElementById('collapse-btn');
    panel.classList.toggle('collapsed', calCollapsed);
    btn.textContent = calCollapsed ? '◀' : '▶';
}

// ── Panel resizing ──
// Each resizer is identified by data-resize and walks up to .main to set
// the correct CSS variables on a width pair. We don't rely on DOM siblings
// because flex `order` reshuffles the visual layout when chat docks.
(function () {
    const MIN_PANEL_W = 180;

    function panelWidth(el) {
        return el ? el.getBoundingClientRect().width : 0;
    }

    function startResize(handle, e) {
        e.preventDefault();
        const main = document.querySelector(".main");
        const chatPanel = document.getElementById("chat-panel");
        const searchPanel = document.querySelector(".search-panel");
        const calPanel = document.getElementById("cal-panel");
        const kind = handle.dataset.resize;

        // Decide which two panels this handle resizes, and which CSS vars to set.
        // `left` is the panel to the visual left, `right` to the visual right.
        let left, right, leftVar, rightVar;
        if (kind === "search-cal") {
            left = searchPanel;
            right = calPanel;
            leftVar = "--search-width";
            rightVar = "--cal-width";
        } else if (kind === "chat-side") {
            // Position depends on which side chat is docked
            if (chatPanel.classList.contains("docked-left")) {
                left = chatPanel; right = searchPanel;
                leftVar = "--chat-width"; rightVar = "--search-width";
            } else if (chatPanel.classList.contains("docked-right")) {
                left = calPanel; right = chatPanel;
                leftVar = "--cal-width"; rightVar = "--chat-width";
            } else {
                return; // resizer shouldn't be visible/active when undocked
            }
        } else {
            return;
        }

        const startX = e.clientX;
        const startLeftW = panelWidth(left);
        const startRightW = panelWidth(right);

        handle.classList.add("resizing");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";

        function onMove(ev) {
            const dx = ev.clientX - startX;
            const newLeftW = startLeftW + dx;
            const newRightW = startRightW - dx;
            if (newLeftW < MIN_PANEL_W || newRightW < MIN_PANEL_W) return;
            main.style.setProperty(leftVar, newLeftW + "px");
            main.style.setProperty(rightVar, newRightW + "px");
        }

        function onUp() {
            handle.classList.remove("resizing");
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
        }

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".panel-resizer").forEach(function (handle) {
            handle.addEventListener("mousedown", function (e) { startResize(handle, e); });
        });
    });
})();

// ── Conflict detection ──
function getSectionSlots(sec) {
    return getMeetingSlots(sec).map(({ dayIdx, start, end }) => ({
        dayIdx, start: timeToFrac(start), end: timeToFrac(end)
    }));
}

function detectConflicts(newLecture, newRecitation) {
    const newSlots = [
        ...getSectionSlots(newLecture),
        ...(newRecitation ? getSectionSlots(newRecitation) : [])
    ];
    const conflicts = [];
    schedule.forEach(({ lecture, recitation, color }) => {
        const existingSlots = [
            ...getSectionSlots(lecture),
            ...(recitation ? getSectionSlots(recitation) : [])
        ];
        for (const ns of newSlots) {
            for (const es of existingSlots) {
                if (ns.dayIdx === es.dayIdx && ns.start < es.end && ns.end > es.start) {
                    conflicts.push(lecture.code);
                    return;
                }
            }
        }
    });
    return [...new Set(conflicts)];
}

// ── Dropdowns ──
async function loadDropdown(url, selId) {
    const res = await fetch(url);
    const items = await res.json();
    const sel = document.getElementById(selId);
    items.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v; opt.textContent = v;
        sel.appendChild(opt);
    });
}

// ── Search ──
function isSecondarySection(c) {
    const comp = (c.component || "").toLowerCase();
    return comp.includes("rct") || comp.includes("recitation") || comp.includes("lab") || comp.includes("laboratory");
}

function sectionTypeLabel(c) {
    const comp = (c.component || "").toLowerCase();
    if (comp.includes("lab") || comp.includes("laboratory")) return "Laboratory";
    if (comp.includes("rct") || comp.includes("recitation")) return "Recitation";
    return c.component || "Section";
}

function renderCourseSections(sections) {
    const lectures = sections.filter(c => !isSecondarySection(c));
    const secondaries = sections.filter(c => isSecondarySection(c));

    // Show lectures with their recitations/labs directly beneath them so the
    // user can see the full section structure before deciding to add anything.
    return lectures.length > 0
        ? lectures.map(lec => {
            const related = recitationsForLecture(lec.section, sections);
            return [renderSection(lec, false), ...related.map(sec => renderSection(sec, true))].join("");
        }).join("")
        : secondaries.map(sec => renderSection(sec, true)).join("");
}

function isSectionAdded(crn) {
    return schedule.some(e => e.lecture.crn === crn || (e.recitation && e.recitation.crn === crn));
}

function handleRemoveByCrn(crn) {
    const idx = schedule.findIndex(e =>
        e.lecture.crn === crn || (e.recitation && e.recitation.crn === crn)
    );
    if (idx !== -1) removeEntry(idx);
}

function statusBadge(raw) {
    const s = (raw || "").trim();
    const lower = s.toLowerCase();
    if (!s) return "";
    let cls = "status-open";
    if (lower === "closed") cls = "status-closed";
    else if (lower.startsWith("wait list") || lower.startsWith("waitlist")) cls = "status-waitlist";
    else if (lower === "cancelled") cls = "status-cancelled";
    return `<span class="status-badge ${cls}">${s}</span>`;
}

function renderSection(c, isSecondary) {
    const added = isSectionAdded(c.crn);
    const btn = added
        ? `<button class="add-btn added"
          onclick="handleRemoveByCrn('${c.crn}')"
          onmouseenter="this.textContent='Remove'"
          onmouseleave="this.textContent='Added'">Added</button>`
    : `<button class="add-btn" onclick="handleAdd('${c.crn}')">Add</button>`;
  const ratings = Array.isArray(c.professor_ratings) && c.professor_ratings.length
    ? c.professor_ratings
    : (c.professor_rating ? [c.professor_rating] : []);
  const ratingHtml = ratings.map(rating => {
    const ratingParts = [];
    if (rating && typeof rating.rating === "number") ratingParts.push(`RMP ${rating.rating.toFixed(1)}/5`);
    if (rating && typeof rating.rating_count === "number") ratingParts.push(`${rating.rating_count} ratings`);
    if (rating && typeof rating.would_take_again_percent === "number") ratingParts.push(`${rating.would_take_again_percent}% again`);
    if (!rating || !rating.url || !ratingParts.length) return "";
    const label = rating.found_name && ratings.length > 1 ? `${rating.found_name}: ` : "";
    return `<div class="section-rating"><a href="${rating.url}" target="_blank" rel="noopener noreferrer">${label}${ratingParts.join(" · ")}</a></div>`;
  }).join("");
  const topic = topicText(c);
  const topicHtml = topic ? `<span class="section-topic">Topic: ${escapeHtml(topic)}</span>` : "";
  const instructorLinks = (c.instructor || "")
    .split(/\s*(?:;|\/|\||&| and )\s*/i)
    .map(name => name.trim())
    .filter(Boolean)
    .map(name => `<a class="instructor-link" href="/professor?name=${encodeURIComponent(name)}">${name}</a>`)
    .join(" · ");
  return `
      <div class="section-row${isSecondary ? " rct-row" : ""}" data-crn="${c.crn}" data-section="${c.section || ""}">
      <div class="section-left">
                <span class="section-type">${sectionTypeLabel(c)}</span>
        <span class="section-num">Sec ${c.section} · Class# ${c.crn}</span>
        ${c.location ? `<span class="section-loc">${c.location}</span>` : ""}
      </div>
      <div class="section-mid">
        ${topicHtml}
        ${instructorLinks ? `<span><strong>${instructorLinks}</strong></span>` : ""}
        ${ratingHtml}
        ${c.meets_human ? `<span>${c.meets_human}</span>` : ""}
        ${statusBadge(c.status)}
      </div>
            <div>${isSecondary ? "" : btn}</div>
    </div>`;
}

function renderCourseGroup(code, title, description, school, sections) {
    sections.forEach(s => { sectionMap[s.crn] = s; });
    const firstSection = sections[0] || {};
    const visibleRows = renderCourseSections(sections);

    return `
    <div class="course-card" data-code="${code}">
      <div class="course-title-row">
        <span class="course-code-label">${code}</span>
        <span class="course-title-text">${title}</span>
        <button class="reload-btn"
                data-code="${code}"
                data-crn="${firstSection.crn || ""}"
                data-section="${firstSection.section || ""}"
                onclick="reloadCourseFromBulletin(this)">Reload</button>
      </div>
      ${school ? `<div class="course-school">${school}</div>` : ""}
      ${description ? `
        <div class="course-description">${description}</div>
        <button class="desc-toggle" onclick="toggleDescription(this)">Show more</button>
      ` : ""}
      <div class="sections-table" data-sections-for="${code}">${visibleRows}</div>
    </div>`;
}

async function hydrateCourseSections(term, source = "albert") {
    const cards = document.querySelectorAll('.course-card[data-code]');
    await Promise.all([...cards].map(async card => {
        const code = card.dataset.code;
        const target = card.querySelector('.sections-table[data-sections-for]');
        if (!code || !target) return;

        try {
            const params = new URLSearchParams({ code, source });
            if (term) params.set("term", term);
            const res = await fetch(`/api/classes?${params}`);
            const data = await res.json();
            if (!res.ok || !Array.isArray(data.classes) || !data.classes.length) return;

            data.classes.forEach(s => { sectionMap[s.crn] = s; });

            const existingLectureRows = [...target.querySelectorAll('.section-row[data-section]:not(.rct-row)')];
            for (const row of existingLectureRows) {
                const lectureSec = row.dataset.section;
                if (!lectureSec) continue;

                const related = recitationsForLecture(lectureSec, data.classes)
                    .filter(sec => !target.querySelector(`.section-row[data-crn="${sec.crn}"]`));
                if (!related.length) continue;

                row.insertAdjacentHTML("afterend", related.map(sec => renderSection(sec, true)).join(""));
            }
        } catch (e) {
            console.warn(`Failed to hydrate sections for ${code}:`, e);
        }
    }));
}

function toggleDescription(button) {
    const description = button.previousElementSibling;
    if (!description) return;
    const expanded = description.classList.toggle("expanded");
    button.textContent = expanded ? "Show less" : "Show more";
}

async function reloadCourseFromBulletin(button) {
    const card = button.closest(".course-card");
    const term = document.getElementById("term").value;
    const payload = {
        term,
        code: button.dataset.code,
        crn: button.dataset.crn,
        section: button.dataset.section,
    };

    button.disabled = true;
    button.textContent = "Reloading";
    try {
        const res = await fetch("/api/classes/reload", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Reload failed");
        displayBulletinCourse(card, data.course || {});
        button.textContent = "Reloaded";
    } catch (e) {
        button.textContent = "Failed";
        alert(e.message);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            if (button.textContent !== "Reload") button.textContent = "Reload";
        }, 1600);
    }
}

function displayBulletinCourse(card, course) {
    if (!card) return;

    const title = card.querySelector(".course-title-text");
    if (title && course.title) title.textContent = course.title;

    let description = card.querySelector(".course-description");
    if (!description && course.description) {
        description = document.createElement("div");
        description.className = "course-description";
        card.querySelector(".sections-table")?.before(description);
    }
    if (description && course.description) description.textContent = course.description;

    let meta = card.querySelector(".bulletin-meta");
    if (!meta) {
        meta = document.createElement("div");
        meta.className = "bulletin-meta";
        card.querySelector(".sections-table")?.before(meta);
    }
    const details = [course.section ? `Sec ${course.section}` : "", course.crn ? `Class# ${course.crn}` : "", course.status || "", course.scraped_at ? "bulletin reload complete" : "bulletin data"];
    meta.textContent = details.filter(Boolean).join(" · ");
}

let currentPage = 1;

function renderPagination(page, totalPages, totalCourses) {
    const div = document.getElementById("pagination");
    if (totalPages <= 1) { div.style.display = "none"; return; }
    div.style.display = "flex";

    const range = [];
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
            range.push(i);
        } else if (range[range.length - 1] !== "…") {
            range.push("…");
        }
    }

    let html = `<button onclick="search(${page - 1})" ${page === 1 ? "disabled" : ""}>← Prev</button>`;
    range.forEach(p => {
        if (p === "…") html += `<button disabled>…</button>`;
        else html += `<button class="${p === page ? "active" : ""}" onclick="search(${p})">${p}</button>`;
    });
    html += `<button onclick="search(${page + 1})" ${page === totalPages ? "disabled" : ""}>Next →</button>`;
    html += `<span class="pagination-info">${totalCourses} course${totalCourses !== 1 ? "s" : ""} · page ${page} of ${totalPages}</span>`;
    div.innerHTML = html;
}

async function search(page = 1) {
    currentPage = page;
    const term = document.getElementById("term").value;
    const q = document.getElementById("query").value.trim();
    const school = document.getElementById("school").value;
    const component = document.getElementById("component").value;
    const status = document.getElementById("status").value;
    const resultsDiv = document.getElementById("results");
    const countDiv = document.getElementById("results-count");

    resultsDiv.innerHTML = '<div class="loading">Searching…</div>';
    countDiv.textContent = "";
    document.getElementById("pagination").style.display = "none";

    try {
        const params = new URLSearchParams({ term, page });
        if (q) params.append("q", q);
        if (school) params.append("school", school);
        if (component) params.append("component", component);
        if (status) params.append("status", status);

        const urlState = new URLSearchParams({ term, page });
        if (q) urlState.append("q", q);
        if (school) urlState.append("school", school);
        if (component) urlState.append("component", component);
        if (status) urlState.append("status", status);
        history.replaceState({}, "", "?" + urlState);

        const res = await fetch(`/api/classes?${params}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");

        const classes = data.classes || [];
        const groups = new Map();
        classes.forEach(c => {
            if (!groups.has(c.code)) groups.set(c.code, { title: c.title, description: c.description, school: c.school, sections: [] });
            groups.get(c.code).sections.push(c);
        });

        let html = "";
        groups.forEach(({ title, description, school, sections }, code) => {
            html += renderCourseGroup(code, title, description, school, sections);
        });

        countDiv.textContent = `Showing ${groups.size} course${groups.size !== 1 ? "s" : ""} (${classes.length} sections)`;
        resultsDiv.innerHTML = groups.size ? html : '<div class="course-card">No courses found.</div>';
        updateDescriptionToggles();
        await hydrateCourseSections(term, "albert");
        renderPagination(data.page, data.total_pages, data.total_courses);
        resultsDiv.scrollTop = 0;
    } catch (e) {
        resultsDiv.innerHTML = `<div class="error">Error: ${e.message}</div>`;
    }
}

// ── Add to schedule ──
function updateDescriptionToggles() {
    document.querySelectorAll(".course-description").forEach(description => {
        const button = description.nextElementSibling;
        if (!button || !button.classList.contains("desc-toggle")) return;
        button.style.display = description.scrollHeight > description.clientHeight + 2 ? "" : "none";
    });
}

// Find the secondary sections that belong to a given lecture section.
// Convention: a secondary section pairs with the largest lecture section number
// that is <= the secondary section's section number.
function recitationsForLecture(lectureSec, allSections) {
    const lectures = allSections.filter(c => !isSecondarySection(c));
    const secondaries = allSections.filter(c => isSecondarySection(c));
    if (lectures.length <= 1) return secondaries;

    const sortValue = value => {
        const raw = String(value || "").trim();
        const numeric = raw.match(/\d+/)?.[0];
        return numeric ? Number(numeric) : raw;
    };

    const lecSections = lectures
        .map(l => ({ section: l.section, sortKey: sortValue(l.section) }))
        .sort((a, b) => {
            if (typeof a.sortKey === "number" && typeof b.sortKey === "number") return a.sortKey - b.sortKey;
            return String(a.sortKey).localeCompare(String(b.sortKey));
        });

    const matched = secondaries.filter(sec => {
        const secKey = sortValue(sec.section);
        let parent = lecSections[0].section;
        for (const lec of lecSections) {
            const lecKey = lec.sortKey;
            if (
                (typeof lecKey === "number" && typeof secKey === "number" && lecKey <= secKey) ||
                (typeof lecKey !== "number" && typeof secKey !== "number" && String(lecKey) <= String(secKey))
            ) {
                parent = lec.section;
            }
        }
        return parent === lectureSec;
    });

    return matched.length ? matched : secondaries;
}

async function handleAdd(crn) {
    let sec = sectionMap[crn];
    if (!sec) return;

    const addBtn = document.querySelector(`.section-row[data-crn="${crn}"] .add-btn`);
    const originalLabel = addBtn ? addBtn.textContent : "";
    if (addBtn) { addBtn.disabled = true; addBtn.textContent = "Loading…"; }

    // Always fetch the full section list for this course code so we have every
    // recitation, even when the current search filtered them out (e.g. by
    // professor/instructor query, where recitations are taught by TAs).
    let allSections = null;
    try {
        const term = document.getElementById("term")?.value || "";
        const params = new URLSearchParams({ term, code: sec.code });
        const res = await fetch(`/api/classes?${params}`);
        const data = await res.json();
        if (res.ok && Array.isArray(data.classes) && data.classes.length) {
            allSections = data.classes;
            allSections.forEach(s => { sectionMap[s.crn] = s; });
            sec = sectionMap[crn] || sec;
        }
    } catch (e) {
        console.warn("Failed to fetch full course sections:", e);
    }

    if (addBtn) { addBtn.disabled = false; addBtn.textContent = originalLabel || "Add"; }

    // Fall back to whatever we already had if the fetch failed
    if (!allSections) allSections = Object.values(sectionMap).filter(s => s && s.code === sec.code);

    const myRcts = recitationsForLecture(sec.section, allSections);
    if (myRcts.length > 0) openModal(sec, myRcts);
    else addToSchedule(sec, null);
}

function addToSchedule(lecture, recitation) {
    const conflicts = detectConflicts(lecture, recitation);
    if (conflicts.length > 0) {
        const ok = confirm(`⚠️ Time conflict with: ${conflicts.join(", ")}.\n\nAdd anyway?`);
        if (!ok) return;
    }
    const color = COLORS[colorIdx % COLORS.length];
    colorIdx++;
    schedule.push({ lecture, recitation, color });
    saveSchedule();
    renderCalendar();
    renderSelectedList();
    document.querySelectorAll(`.section-row[data-crn="${lecture.crn}"] .add-btn`).forEach(b => {
        b.textContent = "Added";
        b.classList.add("added");
        b.disabled = false;
        b.onclick = () => handleRemoveByCrn(lecture.crn);
        b.onmouseenter = () => { b.textContent = "Remove"; };
        b.onmouseleave = () => { b.textContent = "Added"; };
    });
}

// ── Modal ──
function openModal(lecture, rcts) {
  pendingLecture = lecture; pendingRcts = rcts; selectedRct = null;
  document.getElementById("modal-title").textContent = `${lecture.code} — ${lecture.title}`;
  const topic = topicText(lecture);
  const details = [
    `Lecture Sec ${lecture.section}`,
    topic ? `Topic: ${topic}` : "",
    lecture.meets_human || "",
  ].filter(Boolean).join(" | ");
  document.getElementById("modal-subtitle").textContent = `${details} - Pick a recitation:`;
  document.getElementById("modal-confirm").disabled = true;
  document.getElementById("modal-rct-list").innerHTML = rcts.map((r, i) => `
    <div class="modal-rct-row" onclick="selectRct(${i})" id="rct-opt-${i}">
      <span><strong>Sec ${r.section}</strong> &nbsp; ${r.meets_human || "TBA"}</span>
      <span style="color:#888;font-size:0.78rem">${r.instructor || ""}${r.campus_location ? " · " + r.campus_location : ""}</span>
    </div>`).join("");
    document.getElementById("modal").classList.add("open");
}

function selectRct(i) {
    selectedRct = pendingRcts[i];
    document.querySelectorAll(".modal-rct-row").forEach((el, j) => el.classList.toggle("selected-rct", i === j));
    document.getElementById("modal-confirm").disabled = false;
}

function confirmSelection() {
    if (!pendingLecture || !selectedRct) return;
    addToSchedule(pendingLecture, selectedRct);
    closeModal();
}

function closeModal() {
    document.getElementById("modal").classList.remove("open");
    pendingLecture = null; pendingRcts = []; selectedRct = null;
}

// ── Calendar rendering ──
function renderCalendar() {
    const grid = document.getElementById("cal-grid");
    let html = `<div class="cal-day-header" style="grid-column:1"></div>`;
    DAYS.forEach(d => { html += `<div class="cal-day-header">${d}</div>`; });

    for (let h = HOUR_START; h < HOUR_END; h++) {
        const label = h < 12 ? `${h}am` : h === 12 ? "12pm" : `${h - 12}pm`;
        html += `<div class="cal-time-col">${label}</div>`;
        for (let d = 0; d < 5; d++) {
            html += `<div class="cal-cell" data-day="${d}" data-hour="${h}"></div>`;
        }
    }

    grid.innerHTML = html;

    if (schedule.length === 0) {
        grid.innerHTML += `<div class="cal-empty">Add courses to see them here</div>`;
        return;
    }

    schedule.forEach(({ lecture, recitation, color }) => {
        [lecture, recitation].filter(Boolean).forEach(sec => {
            getMeetingSlots(sec).forEach(({ dayIdx, start, end }) => {
                const startFrac = timeToFrac(start);
                const endFrac   = timeToFrac(end);
                const hourCell  = Math.floor(startFrac);
                if (hourCell < HOUR_START || hourCell >= HOUR_END) return;

                const cell = grid.querySelector(`[data-day="${dayIdx}"][data-hour="${hourCell}"]`);
                if (!cell) return;

                const offsetPx  = (startFrac - hourCell) * PX_PER_HOUR;
                const heightPx  = (endFrac - startFrac) * PX_PER_HOUR;

                const ev = document.createElement("div");
                ev.className = "cal-event";
                ev.dataset.dayIdx = dayIdx;
                ev.dataset.start = startFrac;
                ev.dataset.end = endFrac;
                ev.style.cssText = `top:${offsetPx}px;height:${heightPx}px;background:${color};`;
                const topic = topicText(sec);
                ev.innerHTML = `
                  <strong>${sec.code}</strong>
                  ${topic ? `<span>${escapeHtml(topic)}</span>` : ""}
                  <span>${sec.meets_human || ""}</span>
                `;
                cell.appendChild(ev);
            });
        });
    });

    // Highlight conflicts
    const events = [...grid.querySelectorAll(".cal-event")];
    events.forEach((a, i) => {
        events.slice(i + 1).forEach(b => {
            if (a.dataset.dayIdx === b.dataset.dayIdx &&
                parseFloat(a.dataset.start) < parseFloat(b.dataset.end) &&
                parseFloat(a.dataset.end) > parseFloat(b.dataset.start)) {
                a.style.outline = "2px solid red";
                b.style.outline = "2px solid red";
            }
        });
    });
}

function renderSelectedList() {
  const container = document.getElementById("selected-list-items");
  if (schedule.length === 0) {
    container.innerHTML = '<div style="color:#bbb;font-size:0.76rem">No courses added yet</div>';
    return;
  }
  container.innerHTML = schedule.map((e, i) => {
    const topic = topicText(e.lecture);
    return `
      <div class="selected-item">
        <div class="color-dot" style="background:${e.color}"></div>
        <span>${e.lecture.code} Sec ${e.lecture.section}${topic ? " - " + escapeHtml(topic) : ""}${e.recitation ? " + Rct " + e.recitation.section : ""}</span>
        <button class="remove-btn" onclick="removeEntry(${i})">✕</button>
      </div>`;
  }).join("");
}

function removeEntry(i) {
    schedule.splice(i, 1);
    saveSchedule();
    renderCalendar();
    renderSelectedList();
    search(currentPage);
}

function clearSchedule() {
    schedule = []; colorIdx = 0;
    saveSchedule();
    renderCalendar();
    renderSelectedList();
    search(currentPage);
}

document.getElementById("modal").addEventListener("click", function (e) { if (e.target === e.currentTarget) closeModal(); });

// ── Export .ics ──
function downloadCalendar() {
  if (schedule.length === 0) { alert("No courses in your schedule to export."); return; }

  const term = document.getElementById("term").value;
  const SEMESTERS = {
    "1264": { name: "Spring 2026", monday: [2026, 0, 26], until: "20260515T235959Z" },
    "1266": { name: "Summer 2026", monday: [2026, 4, 18], until: "20260814T235959Z" },
    "1268": { name: "Fall 2026",   monday: [2026, 8,  7], until: "20261218T235959Z" },
  };
  const sem = SEMESTERS[term] || SEMESTERS["1268"];
  const semMonday = new Date(sem.monday[0], sem.monday[1], sem.monday[2]);
  const DAY_CODES = ["MO", "TU", "WE", "TH", "FR"];

  function pad2(n) { return String(n).padStart(2, "0"); }
  function icsDate(date) {
    return `${date.getFullYear()}${pad2(date.getMonth() + 1)}${pad2(date.getDate())}`;
  }
  function icsTime(hhmm) {
    return hhmm.replace(":", "") + "00";
  }
  function escape(s) {
    return (s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
  }

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//NYU Course Planner//EN",
    "CALSCALE:GREGORIAN",
    `X-WR-CALNAME:NYU ${sem.name} Schedule`,
    "X-WR-TIMEZONE:America/New_York",
  ];

  let uid = 0;
  schedule.forEach(({ lecture, recitation }) => {
    [lecture, recitation].filter(Boolean).forEach(sec => {
      (sec.meeting_times || []).forEach(mt => {
        if (!mt.start || !mt.end || typeof mt.day_num !== "number") return;
        if (mt.day_num < 0 || mt.day_num > 4) return;

        // First occurrence = semester Monday + day offset
        const firstDay = new Date(semMonday);
        firstDay.setDate(firstDay.getDate() + mt.day_num);
        const dateStr = icsDate(firstDay);

        const topic = topicText(sec);
        const summary = escape(`${sec.code}${sec.title ? " - " + sec.title : ""}${topic ? " - " + topic : ""}`);
        const desc = [
          topic          ? `Topic: ${topic}` : "",
          sec.instructor ? `Instructor: ${sec.instructor}` : "",
          sec.component  ? `Type: ${sec.component}` : "",
          sec.section    ? `Section: ${sec.section}` : "",
          sec.crn        ? `Class#: ${sec.crn}` : "",
        ].filter(Boolean).map(escape).join("\\n");

        lines.push(
          "BEGIN:VEVENT",
          `UID:nyu-${sec.crn}-${mt.day_num}-${++uid}@nyu-planner`,
          `SUMMARY:${summary}`,
          `DTSTART;TZID=America/New_York:${dateStr}T${icsTime(mt.start)}`,
          `DTEND;TZID=America/New_York:${dateStr}T${icsTime(mt.end)}`,
          `RRULE:FREQ=WEEKLY;BYDAY=${DAY_CODES[mt.day_num]};UNTIL=${sem.until}`,
          ...(desc ? [`DESCRIPTION:${desc}`] : []),
          ...(sec.location ? [`LOCATION:${escape(sec.location)}`] : []),
          "END:VEVENT",
        );
      });
        });
    });

        lines.push("END:VCALENDAR");

    const blob = new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `NYU_${sem.name.replace(" ", "_")}_Schedule.ics`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

let _searchDebounce = null;
function debounceSearch(page = 1, delay = 350) {
    clearTimeout(_searchDebounce);
    _searchDebounce = setTimeout(() => search(page), delay);
}

async function init() {
    renderCalendar();
    renderSelectedList();

    await loadDropdown("/api/schools", "school");

    // Restore URL state first so dropdowns have the right values before first search
    const urlp = new URLSearchParams(window.location.search);
    if (urlp.get("term")) document.getElementById("term").value = urlp.get("term");
    if (urlp.get("q")) document.getElementById("query").value = urlp.get("q");
    if (urlp.get("school")) document.getElementById("school").value = urlp.get("school");
    if (urlp.get("component")) document.getElementById("component").value = urlp.get("component");
    if (urlp.get("status")) document.getElementById("status").value = urlp.get("status");

    // All dropdowns auto-filter immediately on change
    ["term", "school", "component", "status"].forEach(id => {
        document.getElementById(id).addEventListener("change", () => debounceSearch(1, 0));
    });
    // Text input debounces so rapid typing only fires one request
    document.getElementById("query").addEventListener("input", () => debounceSearch(1, 350));
    document.getElementById("query").addEventListener("keydown", e => {
        if (e.key === "Enter") { clearTimeout(_searchDebounce); search(1); }
    });

    // Wire up the Search button
    const searchBtn = document.getElementById("search-btn");
    if (searchBtn) {
        searchBtn.addEventListener("click", () => { clearTimeout(_searchDebounce); search(1); });
    }

    // Always load courses on page open
    search(parseInt(urlp.get("page") || "1"));
}

init();

// ── AI Chat ──
let chatOpen = false;
let contextOpen = false;

// ── Chat panel drag + side-panel docking ──
(function () {
    const SNAP_THRESHOLD = 80; // px from left/right edge to trigger dock

    let dragging = false;
    let didDrag = false;
    let startX = 0, startY = 0, startLeft = 0, startTop = 0;
    // Preview indicator shown while hovering near an edge during drag
    let snapPreview = null;

    function getSnapPreview() {
        if (!snapPreview) {
            snapPreview = document.createElement("div");
            snapPreview.id = "chat-snap-preview";
            document.body.appendChild(snapPreview);
        }
        return snapPreview;
    }

    function showPreview(side) {
        const el = getSnapPreview();
        el.className = "snap-preview-" + side;
        el.style.display = "block";
    }

    function hidePreview() {
        if (snapPreview) snapPreview.style.display = "none";
    }

    function isDocked() {
        const panel = document.getElementById("chat-panel");
        return panel.classList.contains("docked-left") || panel.classList.contains("docked-right");
    }

    function dock(side) {
        const panel = document.getElementById("chat-panel");
        const main = document.querySelector(".main");

        // Clear any inline float positioning
        panel.style.left = "";
        panel.style.top = "";
        panel.style.right = "";
        panel.style.bottom = "";
        panel.style.width = "";
        panel.style.height = "";
        panel.style.position = "";
        panel.style.transform = "";

        // Ensure we don't carry the wrong dock side (left ↔ right toggle)
        main.classList.remove("chat-docked-left", "chat-docked-right");
        panel.classList.remove("docked-left", "docked-right", "open");
        panel.classList.add("docked-" + side);
        main.classList.add("chat-docked-" + side);
    }

    function undock() {
        const panel = document.getElementById("chat-panel");
        const main = document.querySelector(".main");

        panel.classList.remove("docked-left", "docked-right");
        main.classList.remove("chat-docked-left", "chat-docked-right");
        // Drop pixel widths set while docked so search/cal grow back to defaults
        main.style.removeProperty("--search-width");
        main.style.removeProperty("--cal-width");

        // Restore floating position (centered above bubble)
        panel.style.position = "fixed";
        panel.style.left = "50%";
        panel.style.bottom = "76px";
        panel.style.right = "";
        panel.style.top = "";
        panel.style.width = "";
        panel.style.height = "";
        panel.style.transform = "";

        // Re-open as floating overlay
        panel.classList.add("open");
        chatOpen = true;
    }

    function onMouseDown(e) {
        if (e.target.closest("#chat-close-btn")) return;
        const panel = document.getElementById("chat-panel");

        if (isDocked()) {
            // Start drag from docked state — pull it out
            const rect = panel.getBoundingClientRect();
            undock();
            // Reposition under cursor so it doesn't jump
            panel.style.left = (e.clientX - rect.width / 2) + "px";
            panel.style.top = rect.top + "px";
            panel.style.right = "auto";
            panel.style.bottom = "auto";
            startX = e.clientX;
            startY = e.clientY;
            startLeft = e.clientX - rect.width / 2;
            startTop = rect.top;
        } else {
            const rect = panel.getBoundingClientRect();
            // Kill the centering transform before setting left/top,
            // otherwise translateX(-50%) stacks on top of the explicit left value
            panel.style.transform = "none";
            panel.style.left = rect.left + "px";
            panel.style.top = rect.top + "px";
            panel.style.right = "auto";
            panel.style.bottom = "auto";
            startX = e.clientX;
            startY = e.clientY;
            startLeft = rect.left;
            startTop = rect.top;
        }

        dragging = true;
        didDrag = false;
        panel.classList.add("dragging");
        e.preventDefault();
    }

    function onMouseMove(e) {
        if (!dragging) return;
        didDrag = true;
        const panel = document.getElementById("chat-panel");
        const panelW = panel.getBoundingClientRect().width;
        const panelH = panel.getBoundingClientRect().height;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        // Allow panel to slide far enough to reach either snap zone
        const newLeft = Math.max(-panelW + SNAP_THRESHOLD + 1,
                                 Math.min(startLeft + dx, window.innerWidth - SNAP_THRESHOLD - 1));
        const newTop = Math.max(0, Math.min(startTop + dy, window.innerHeight - panelH));
        panel.style.left = newLeft + "px";
        panel.style.top = newTop + "px";

        // Show snap preview hint
        if (newLeft <= SNAP_THRESHOLD) {
            showPreview("left");
        } else if (newLeft + panelW >= window.innerWidth - SNAP_THRESHOLD) {
            showPreview("right");
        } else {
            hidePreview();
        }
    }

    function onMouseUp() {
        if (!dragging) return;
        dragging = false;
        hidePreview();
        const panel = document.getElementById("chat-panel");
        panel.classList.remove("dragging");

        if (!didDrag) return;

        const left = parseFloat(panel.style.left);
        const panelW = panel.getBoundingClientRect().width;
        if (left <= SNAP_THRESHOLD) {
            dock("left");
        } else if (left + panelW >= window.innerWidth - SNAP_THRESHOLD) {
            dock("right");
        } else {
            // Floating free — keep explicit left/top, no centering transform needed
            panel.style.transform = "none";
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.getElementById("chat-panel-header").addEventListener("mousedown", onMouseDown);
    });
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
})();

function toggleChat() {
    const panel = document.getElementById("chat-panel");
    const main = document.querySelector(".main");
    const docked = panel.classList.contains("docked-left") || panel.classList.contains("docked-right");
    if (docked) {
        // Closing while docked: fully remove from layout
        panel.classList.remove("docked-left", "docked-right");
        main.classList.remove("chat-docked-left", "chat-docked-right");
        // Drop pixel widths set while docked so search/cal grow back to defaults
        main.style.removeProperty("--search-width");
        main.style.removeProperty("--cal-width");
        panel.style.position = "fixed";
        panel.style.left = "50%";
        panel.style.bottom = "76px";
        panel.style.right = "";
        panel.style.top = "";
        panel.style.width = "";
        panel.style.height = "";
        panel.style.transform = "";
        chatOpen = false;
        return;
    }
    chatOpen = !chatOpen;
    panel.classList.toggle("open", chatOpen);
    if (chatOpen) document.getElementById("chat-input").focus();
}

function toggleContext() {
    contextOpen = !contextOpen;
    document.getElementById("chat-context-fields").style.display = contextOpen ? "flex" : "none";
    document.getElementById("chat-context-arrow").textContent = contextOpen ? "▾" : "▸";
}

function appendMsg(text, role) {
    const box = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    div.textContent = text;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
}

function renderMarkdown(div, text) {
    if (window.marked) {
        div.innerHTML = marked.parse(text);
    } else {
        div.textContent = text;
    }
}

function autoResizeInput() {
    const el = document.getElementById("chat-input");
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

async function sendChat() {
    const input = document.getElementById("chat-input");
    const btn = document.getElementById("chat-send-btn");
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    input.style.height = "auto";
    btn.disabled = true;
    appendMsg(msg, "user");
    const typing = appendMsg("Thinking…", "ai typing");

    try {
        const major = document.getElementById("chat-major").value.trim();
        const coursesRaw = document.getElementById("chat-courses").value.trim();
        const completed_courses = coursesRaw
            ? coursesRaw.split(",").map(s => s.trim()).filter(Boolean)
            : [];
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg, major, completed_courses }),
        });
        const data = await res.json();
        const reply = data.reply || data.error || "Something went wrong.";
        typing.classList.remove("typing");
        renderMarkdown(typing, reply);
        document.getElementById("chat-messages").scrollTop = 999999;
    } catch {
        typing.textContent = "Network error. Please try again.";
        typing.classList.remove("typing");
    } finally {
        btn.disabled = false;
        input.focus();
    }
}

document.getElementById("chat-input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
document.getElementById("chat-input").addEventListener("input", autoResizeInput);

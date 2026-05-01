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

// ── Calendar collapse ──
let calCollapsed = false;
function toggleCalendar() {
    calCollapsed = !calCollapsed;
    const panel = document.getElementById('cal-panel');
    const btn = document.getElementById('collapse-btn');
    panel.classList.toggle('collapsed', calCollapsed);
    btn.textContent = calCollapsed ? '◀' : '▶';
}

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
function isRecitation(c) {
    const comp = (c.component || "").toLowerCase();
    return comp.includes("rct") || comp.includes("recitation");
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

function renderSection(c, isRct) {
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
    const instructorLinks = (c.instructor || "")
        .split(/\s*(?:;|\/|\||&| and )\s*/i)
        .map(name => name.trim())
        .filter(Boolean)
        .map(name => `<a class="instructor-link" href="/professor?name=${encodeURIComponent(name)}">${name}</a>`)
        .join(" · ");
    return `
    <div class="section-row${isRct ? " rct-row" : ""}" data-crn="${c.crn}">
      <div class="section-left">
        <span class="section-type">${c.component || ""}</span>
        <span class="section-num">Sec ${c.section} · Class# ${c.crn}</span>
        ${c.location ? `<span class="section-loc">${c.location}</span>` : ""}
      </div>
      <div class="section-mid">
        ${instructorLinks ? `<span><strong>${instructorLinks}</strong></span>` : ""}
        ${ratingHtml}
        ${c.meets_human ? `<span>${c.meets_human}</span>` : ""}
        ${statusBadge(c.status)}
      </div>
      <div>${isRct ? "" : btn}</div>
    </div>`;
}

function renderCourseGroup(code, title, description, school, sections) {
    sections.forEach(s => { sectionMap[s.crn] = s; });
    const firstSection = sections[0] || {};
    const lectures = sections.filter(c => !isRecitation(c));
    const rcts = sections.filter(c => isRecitation(c));

    const rctsByLec = new Map(lectures.map(l => [l.section, []]));
    const lecSections = lectures.map(l => l.section).sort();
    rcts.forEach(rct => {
        let parent = lecSections[0];
        for (const ls of lecSections) { if (ls <= rct.section) parent = ls; }
        rctsByLec.get(parent)?.push(rct);
    });

    const sectionsHtml = lectures.map(lec => {
        const myRcts = rctsByLec.get(lec.section) || [];
        return renderSection(lec, false) + myRcts.map(r => renderSection(r, true)).join("");
    }).join("") + (lectures.length === 0 ? rcts.map(r => renderSection(r, true)).join("") : "");

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
      <div class="sections-table">${sectionsHtml}</div>
    </div>`;
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

function handleAdd(crn) {
    const sec = sectionMap[crn];
    if (!sec) return;

    const card = document.querySelector(`.course-card[data-code="${sec.code}"]`);
    const allRows = card ? [...card.querySelectorAll(".section-row")] : [];
    const myRcts = [];
    let foundLec = false;
    for (const row of allRows) {
        if (row.dataset.crn === crn) { foundLec = true; continue; }
        if (foundLec && row.classList.contains("rct-row")) myRcts.push(sectionMap[row.dataset.crn]);
        else if (foundLec && !row.classList.contains("rct-row")) break;
    }

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
    document.getElementById("modal-subtitle").textContent = `Lecture Sec ${lecture.section} · ${lecture.meets_human || ""} — Pick a recitation:`;
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
                const endFrac = timeToFrac(end);
                const hourCell = Math.floor(startFrac);
                if (hourCell < HOUR_START || hourCell >= HOUR_END) return;

                const cell = grid.querySelector(`[data-day="${dayIdx}"][data-hour="${hourCell}"]`);
                if (!cell) return;

                const offsetPx = (startFrac - hourCell) * PX_PER_HOUR;
                const heightPx = (endFrac - startFrac) * PX_PER_HOUR;

                const ev = document.createElement("div");
                ev.className = "cal-event";
                ev.dataset.dayIdx = dayIdx;
                ev.dataset.start = startFrac;
                ev.dataset.end = endFrac;
                ev.style.cssText = `top:${offsetPx}px;height:${heightPx}px;background:${color};`;
                ev.innerHTML = `<strong>${sec.code}</strong><span>${sec.meets_human || ""}</span>`;
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
    container.innerHTML = schedule.map((e, i) => `
    <div class="selected-item">
      <div class="color-dot" style="background:${e.color}"></div>
      <span>${e.lecture.code} Sec ${e.lecture.section}${e.recitation ? " + Rct " + e.recitation.section : ""}</span>
      <button class="remove-btn" onclick="removeEntry(${i})">✕</button>
    </div>`).join("");
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

document.getElementById("modal").addEventListener("click", e => { if (e.target === e.currentTarget) closeModal(); });

// ── Export .ics ──
function downloadCalendar() {
    if (schedule.length === 0) { alert("No courses in your schedule to export."); return; }

    const term = document.getElementById("term").value;
    const SEMESTERS = {
        "1264": { name: "Spring 2026", monday: [2026, 0, 26], until: "20260515T235959Z" },
        "1266": { name: "Summer 2026", monday: [2026, 4, 18], until: "20260814T235959Z" },
        "1268": { name: "Fall 2026", monday: [2026, 8, 7], until: "20261218T235959Z" },
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

                const summary = escape(`${sec.code}${sec.title ? " – " + sec.title : ""}`);
                const desc = [
                    sec.instructor ? `Instructor: ${sec.instructor}` : "",
                    sec.component ? `Type: ${sec.component}` : "",
                    sec.section ? `Section: ${sec.section}` : "",
                    sec.crn ? `Class#: ${sec.crn}` : "",
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

    // Always load courses on page open
    search(parseInt(urlp.get("page") || "1"));
}

init();

// ── AI Chat ──
let chatOpen = false;
let contextOpen = false;

function toggleChat() {
    chatOpen = !chatOpen;
    document.getElementById("chat-panel").classList.toggle("open", chatOpen);
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

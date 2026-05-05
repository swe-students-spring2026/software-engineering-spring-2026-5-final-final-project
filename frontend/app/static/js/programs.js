let allPrograms = [];
let activeUrl = null;

async function loadPrograms() {
    const list = document.getElementById("program-list");
    list.innerHTML = '<div class="loading">Loading…</div>';
    try {
        const res = await fetch("/api/programs");
        allPrograms = await res.json();
        renderList("");
    } catch (e) {
        list.innerHTML = `<div class="loading">Error: ${e.message}</div>`;
    }
}

const SCHOOL_ORDER = [
    "Arts & Science", "Tandon", "Steinhardt", "Tisch", "Stern",
    "Liberal Studies", "Gallatin", "SPS", "Global Public Health",
    "Wagner", "Silver", "Rory Meyers", "Dentistry", "Abu Dhabi", "Shanghai"
];

function renderList(filter) {
    const list = document.getElementById("program-list");
    const f = filter.toLowerCase();
    const filtered = allPrograms.filter(p =>
        !f || (p.title || "").toLowerCase().includes(f) || (p.school || "").toLowerCase().includes(f)
    );
    if (filtered.length === 0) {
        list.innerHTML = '<div class="loading">No programs match.</div>';
        return;
    }

    // Group by school
    const groups = new Map();
    filtered.forEach(p => {
        const school = p.school || "Other";
        if (!groups.has(school)) groups.set(school, []);
        groups.get(school).push(p);
    });

    // Sort schools by preferred order, then alphabetically
    const sortedSchools = [...groups.keys()].sort((a, b) => {
        const ai = SCHOOL_ORDER.indexOf(a), bi = SCHOOL_ORDER.indexOf(b);
        if (ai !== -1 && bi !== -1) return ai - bi;
        if (ai !== -1) return -1;
        if (bi !== -1) return 1;
        return a.localeCompare(b);
    });

    // Expand the group containing the active program, all when filtering, else collapse others
    const isFiltering = f.length > 0;
    const activeSchool = activeUrl ? (allPrograms.find(p => p.url === activeUrl) || {}).school || "Other" : null;

    list.innerHTML = sortedSchools.map((school, i) => {
        const programs = groups.get(school);
        const isActive = school === activeSchool;
        const collapsed = !isFiltering && i !== 0 && !isActive ? " collapsed" : "";
        const items = programs.map(p => `
      <div class="program-item ${p.url === activeUrl ? "active" : ""}" data-url="${encodeURIComponent(p.url)}">
        <div>${p.title || "(untitled)"}</div>
        ${p.award ? `<div class="program-award">${p.award}</div>` : ""}
      </div>`).join("");
        return `
      <div class="school-group${collapsed}" data-school="${school}">
        <div class="school-header" onclick="toggleSchool(this)">
          <span>${school}</span>
          <span style="display:flex;align-items:center;gap:6px">
            <span class="count">${programs.length}</span>
            <span class="chevron">▾</span>
          </span>
        </div>
        <div class="school-programs">${items}</div>
      </div>`;
    }).join("");

    list.querySelectorAll(".program-item").forEach(el => {
        el.addEventListener("click", () => loadDetail(decodeURIComponent(el.dataset.url)));
    });
}

function toggleSchool(header) {
    header.closest(".school-group").classList.toggle("collapsed");
}

function looksLikeCourseCode(s) {
    return /^(or\s+)?[A-Z]{2,5}[-][A-Z]{2,3}[\s\/]/.test(s || "");
}

function isSamplePlan(label) {
    return /sample|plan|semester|term/i.test(label || "");
}

function renderSamplePlan(rows) {
    let html = `<table class="sample-plan-table"><tbody>`;
    rows.forEach(row => {
        const cells = row || [];
        const first = (cells[0] || "").trim();
        const isTermHeader = /^\d+(st|nd|rd|th)\s+Semester/i.test(first) && cells.length === 1;
        const isSubtotal = first === "" && /credits/i.test(cells[1] || "");
        const isGrandTotal = first === "" && /total credits/i.test(cells[1] || "");
        const isTotal = /total\s+credits/i.test(first);

        if (isTermHeader) {
            html += `<tr class="term-header-row"><td colspan="3">${first}</td></tr>`;
        } else if (isGrandTotal || isTotal) {
            const label = isTotal ? first : cells[1];
            const credits = isTotal ? (cells[1] || "") : (cells[2] || "");
            html += `<tr class="total-row"><td colspan="2">${label}</td><td>${credits}</td></tr>`;
        } else if (isSubtotal) {
            html += `<tr class="term-subtotal-row"><td colspan="2">Semester Credits</td><td>${cells[2] || ""}</td></tr>`;
        } else if (looksLikeCourseCode(first)) {
            const title = cells[1] || "";
            const credits = cells[2] || "";
            html += `<tr><td><span class="course-code">${first}</span></td><td>${title}</td><td>${credits}</td></tr>`;
        } else if (first) {
            const credits = cells[1] || cells[2] || "";
            html += `<tr class="plan-elective-row"><td colspan="2">${first}</td><td>${credits}</td></tr>`;
        }
    });
    html += `</tbody></table>`;
    return html;
}

function renderRequirementsTable(rows) {
    let html = `<table><thead><tr><th>Course</th><th>Title</th><th>Credits</th></tr></thead><tbody>`;
    rows.forEach(row => {
        const cells = row || [];
        const first = (cells[0] || "").trim();
        const firstIsCourse = looksLikeCourseCode(first);
        const isAlt = first.toLowerCase().startsWith("or ");
        const isTotal = /total\s+credits/i.test(first);

        if (isTotal) {
            html += `<tr class="total-row"><td colspan="2">${first}</td><td>${cells[1] || ""}</td></tr>`;
        } else if (!firstIsCourse && cells.length <= 2) {
            const rightCol = cells[1] || "";
            const cls = rightCol ? "summary-row" : "section-row";
            html += `<tr class="${cls}"><td colspan="2">${first}</td><td>${rightCol}</td></tr>`;
        } else {
            const title = cells[1] || "";
            const credits = cells.length >= 3 ? cells[2] : "";
            const cls = isAlt ? "alt-row" : "";
            html += `<tr class="${cls}"><td><span class="course-code">${first}</span></td><td>${title}</td><td>${credits}</td></tr>`;
        }
    });
    html += `</tbody></table>`;
    return html;
}

function renderTable(t) {
    if (!t || !t.rows) return "";
    return isSamplePlan(t.label) ? renderSamplePlan(t.rows) : renderRequirementsTable(t.rows);
}

async function loadDetail(url) {
    activeUrl = url;
    renderList(document.getElementById("search").value);
    const detail = document.getElementById("detail");
    detail.innerHTML = '<div class="loading">Loading requirements…</div>';
    try {
        const res = await fetch(`/api/program-requirements?url=${encodeURIComponent(url)}`);
        const p = await res.json();
        if (!res.ok) throw new Error(p.error || "Failed to load");

        let html = `
      <h2>${p.title || ""}</h2>
      <div class="detail-meta">${p.school || ""}${p.award ? " · " + p.award : ""}${p.source?.bulletin_year ? " · " + p.source.bulletin_year : ""}</div>
      <hr class="detail-divider">
    `;
        if (p.program_description) {
            html += `
        <div class="detail-section section-about">
          <div class="detail-section-header"><h3>About</h3></div>
          <div class="detail-section-body"><div class="desc">${p.program_description}</div></div>
        </div>`;
        }
        if (p.tables && p.tables.length) {
            p.tables.forEach(t => {
                const label = t.label || "Course Requirements";
                const plan = isSamplePlan(label);
                const honors = !plan && /honor|supplement/i.test(label);
                const cls = plan ? "section-plan" : honors ? "section-honors" : "section-requirements";
                const badge = plan
                    ? `<span class="section-badge badge-plan">Sample Plan</span>`
                    : honors
                        ? `<span class="section-badge badge-honors">Honors</span>`
                        : `<span class="section-badge badge-requirements">Requirements</span>`;
                html += `
          <div class="detail-section ${cls}">
            <div class="detail-section-header">${badge}<h3>${label}</h3></div>
            <div class="detail-section-body">${renderTable(t)}</div>
          </div>`;
            });
        }
        if (p.policies) {
            html += `
        <div class="detail-section section-policies">
          <div class="detail-section-header"><h3>Policies</h3></div>
          <div class="detail-section-body"><div class="desc">${p.policies}</div></div>
        </div>`;
        }
        detail.innerHTML = html;
    } catch (e) {
        detail.innerHTML = `<div class="loading">Error: ${e.message}</div>`;
    }
}

document.getElementById("search").addEventListener("input", e => renderList(e.target.value));
loadPrograms();

async function fetchProfessorSuggestions() {
    const q = document.getElementById("name").value.trim();
    const term = document.getElementById("term").value;
    const holder = document.getElementById("search-results");
    holder.innerHTML = "";
    if (!q) return;

    const params = new URLSearchParams({ q, limit: "8" });
    if (term) params.set("term", term);
    const res = await fetch(`/api/professors?${params}`);
    const data = await res.json();
    holder.innerHTML = (data.professors || []).map(p =>
        `<button class="search-chip" data-name="${encodeURIComponent(p.name)}">${p.name}</button>`
    ).join("");
    holder.querySelectorAll(".search-chip").forEach(btn => {
        btn.addEventListener("click", () => selectProfessor(decodeURIComponent(btn.dataset.name)));
    });
}

function selectProfessor(name) {
    document.getElementById("name").value = name;
    loadProfessor();
}

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

function sectionSortValue(value) {
  const raw = String(value || "").trim();
  const numeric = raw.match(/\d+/)?.[0];
  return numeric ? Number(numeric) : raw;
}

function recitationsForLecture(lectureSec, allSections) {
  const lectures = allSections.filter(c => !isSecondarySection(c));
  const secondaries = allSections.filter(c => isSecondarySection(c));
  if (lectures.length <= 1) return secondaries;

  const lecSections = lectures
    .map(l => ({ section: l.section, sortKey: sectionSortValue(l.section) }))
    .sort((a, b) => {
      if (typeof a.sortKey === "number" && typeof b.sortKey === "number") return a.sortKey - b.sortKey;
      return String(a.sortKey).localeCompare(String(b.sortKey));
    });

  const matched = secondaries.filter(sec => {
    const secKey = sectionSortValue(sec.section);
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

function renderProfessorSection(section, isSecondary) {
  return `
    <div class="prof-section-row${isSecondary ? " secondary" : ""}">
    <div>
      <div class="prof-section-kind">${sectionTypeLabel(section)}</div>
      <div class="prof-section-meta">Sec ${section.section || ""}${section.crn ? ` · Class# ${section.crn}` : ""}</div>
    </div>
    <div>
      <div class="prof-section-title">${section.title || ""}</div>
      <div class="prof-section-meta">${section.meets_human || "Meeting time TBA"}${section.status ? " · " + section.status : ""}</div>
    </div>
    </div>`;
}

function renderRating(rating) {
    if (!rating) {
        return `
      <div class="rating-box">
        <div class="rating-score">N/A</div>
        <div class="rating-meta">No Rate My Professors result was matched for this instructor yet.</div>
      </div>`;
    }
    return `
    <div class="rating-box">
      <div class="rating-score">${rating.rating.toFixed(1)}/5</div>
      <div class="rating-meta">
        ${rating.rating_count} ratings<br>
        ${rating.would_take_again_percent ?? "N/A"}% would take again<br>
        Difficulty ${rating.difficulty ?? "N/A"}
      </div>
      <a class="rating-link" href="${rating.url}" target="_blank" rel="noopener noreferrer">Open on Rate My Professors</a>
    </div>`;
}

function renderCourses(courses, sectionsByCode = {}) {
    if (!courses.length) return '<div class="empty">No current courses found for this professor.</div>';

    const grouped = new Map();
    courses.forEach(course => {
        const code = course.code || "";
        if (!code) return;
        if (!grouped.has(code)) {
            grouped.set(code, { code, title: course.title || "", sections: [] });
        }
        const entry = grouped.get(code);
        if (!entry.title && course.title) entry.title = course.title;
        entry.sections.push(course);
    });

    return `
    <div class="courses">
      <h3>Courses They Are Teaching</h3>
      ${[...grouped.values()].map(group => {
        const ownSections = group.sections;
        const allSections = sectionsByCode[group.code] || ownSections;
        const lectures = ownSections.filter(c => !isSecondarySection(c));
        const secondaries = ownSections.filter(c => isSecondarySection(c));
        const rows = lectures.length > 0
            ? lectures.map(lec => [
                renderProfessorSection(lec, false),
                ...recitationsForLecture(lec.section, allSections).map(sec => renderProfessorSection(sec, true))
              ].join("")).join("")
            : secondaries.map(sec => renderProfessorSection(sec, true)).join("");

        return `
          <div class="course-item course-item-stack">
            <div class="course-item-head">
              <div>
                <div class="course-code">${group.code}</div>
                <div class="course-sub">${ownSections.length} section${ownSections.length === 1 ? "" : "s"}</div>
              </div>
              <div><strong>${group.title || ""}</strong></div>
            </div>
            <div class="prof-section-list">${rows}</div>
          </div>`;
      }).join("")}
    </div>`;
}

async function loadProfessor() {
    const name = document.getElementById("name").value.trim();
    const term = document.getElementById("term").value;
    const content = document.getElementById("content");
    if (!name) {
        content.innerHTML = '<div class="empty">Enter a professor name first.</div>';
        return;
    }

    history.replaceState({}, "", `/professor?name=${encodeURIComponent(name)}${term ? `&term=${encodeURIComponent(term)}` : ""}`);
    content.innerHTML = '<div class="loading">Loading professor profile...</div>';
    await fetchProfessorSuggestions();

    const params = new URLSearchParams({ name });
    if (term) params.set("term", term);

    const res = await fetch(`/api/professors/profile?${params}`);
    const data = await res.json();
    if (!res.ok) {
        content.innerHTML = `<div class="error">${data.error || "Professor not found."}</div>`;
        return;
    }

    const sectionsByCode = {};
    await Promise.all((data.course_codes || []).map(async code => {
      try {
        const params = new URLSearchParams({ code });
        if (term) params.set("term", term);
        const secRes = await fetch(`/api/classes?${params}`);
        const secData = await secRes.json();
        if (secRes.ok && Array.isArray(secData.classes)) {
          sectionsByCode[code] = secData.classes;
        }
      } catch (e) {
        console.warn(`Failed to load sections for ${code}:`, e);
      }
    }));

    content.innerHTML = `
    <div class="hero-top">
      <div>
        <h2>${data.name}</h2>
        <div class="muted">${data.course_codes.length} distinct course${data.course_codes.length === 1 ? "" : "s"} · ${data.course_count} section${data.course_count === 1 ? "" : "s"}</div>
      </div>
      ${renderRating(data.professor_rating)}
    </div>
    <div style="margin-top:18px">${renderCourses(data.courses, sectionsByCode)}</div>
  `;
}

document.getElementById("name").addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadProfessor();
});
document.getElementById("name").addEventListener("input", () => {
    fetchProfessorSuggestions();
});

if (document.getElementById("name").value.trim()) {
    loadProfessor();
}

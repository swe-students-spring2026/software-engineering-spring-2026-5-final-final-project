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

function renderCourses(courses) {
    if (!courses.length) return '<div class="empty">No current courses found for this professor.</div>';
    return `
    <div class="courses">
      <h3>Courses They Are Teaching</h3>
      ${courses.map(c => `
        <div class="course-item">
          <div>
            <div class="course-code">${c.code}</div>
            <div class="course-sub">${c.component || ""} · Sec ${c.section || ""}</div>
          </div>
          <div>
            <div><strong>${c.title || ""}</strong></div>
            <div class="course-sub">${c.meets_human || "Meeting time TBA"}${c.status ? " · " + c.status : ""}</div>
          </div>
        </div>
      `).join("")}
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

    content.innerHTML = `
    <div class="hero-top">
      <div>
        <h2>${data.name}</h2>
        <div class="muted">${data.course_codes.length} distinct course${data.course_codes.length === 1 ? "" : "s"} · ${data.course_count} section${data.course_count === 1 ? "" : "s"}</div>
      </div>
      ${renderRating(data.professor_rating)}
    </div>
    <div style="margin-top:18px">${renderCourses(data.courses)}</div>
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

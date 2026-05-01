const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const HOUR_START = 8, HOUR_END = 22;
const PX_PER_HOUR = 60;

let schedule = JSON.parse(localStorage.getItem("nyu_schedule") || "[]");
function saveSchedule() { localStorage.setItem("nyu_schedule", JSON.stringify(schedule)); }

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

function fmt12(t) {
  const [h, m] = t.split(':').map(Number);
  const ampm = h < 12 ? 'am' : 'pm';
  return `${h % 12 || 12}:${String(m).padStart(2, '0')}${ampm}`;
}

function renderCalendar() {
  const grid = document.getElementById("cal-grid");

  let html = `<div class="cal-day-header" style="grid-column:1"></div>`;
  DAYS.forEach(d => { html += `<div class="cal-day-header">${d}</div>`; });

  for (let h = HOUR_START; h < HOUR_END; h++) {
    const label = h < 12 ? `${h}am` : h === 12 ? "12pm" : `${h - 12}pm`;
    html += `<div class="cal-time-label">${label}</div>`;
    for (let d = 0; d < 5; d++) {
      html += `<div class="cal-cell" data-day="${d}" data-hour="${h}"></div>`;
    }
  }

  grid.innerHTML = html;

  if (schedule.length === 0) {
    grid.innerHTML += `<div class="cal-empty">No courses yet. <a href="/">Search for courses</a></div>`;
    return;
  }

  schedule.forEach(({ lecture, recitation, color }) => {
    [lecture, recitation].filter(Boolean).forEach(sec => {
      const isRct = recitation && sec.crn === recitation.crn;
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
        ev.style.cssText = `top:${offsetPx}px;height:${heightPx}px;background:${color};opacity:${isRct ? 0.85 : 1};`;
        const topic = topicText(sec);
        ev.innerHTML = `
          <strong>${sec.code}${isRct ? " Rct" : ""}</strong>
          ${topic ? `<span class="ev-sub">${escapeHtml(topic)}</span>` : ""}
          <span class="ev-sub">${fmt12(start)}–${fmt12(end)}</span>
          ${sec.instructor ? `<span class="ev-sub">${sec.instructor}</span>` : ""}
        `;
        cell.appendChild(ev);
      });
    });
  });
}

function renderSidebar() {
  const container = document.getElementById("sidebar-list");
  const summary = document.getElementById("schedule-summary");
  if (schedule.length === 0) {
    container.innerHTML = '<div class="no-courses">No courses selected.</div>';
    summary.textContent = "";
    return;
  }
  summary.textContent = `${schedule.length} course${schedule.length !== 1 ? "s" : ""} selected`;
  container.innerHTML = schedule.map((e, i) => {
    const topic = topicText(e.lecture);
    return `
      <div class="course-entry">
        <div class="course-entry-title">
          <div class="color-dot" style="background:${e.color}"></div>
          <span>${e.lecture.code}</span>
          <button class="remove-btn" onclick="removeEntry(${i})">✕</button>
        </div>
        <div class="course-entry-detail">
          <div><strong>${e.lecture.title}</strong></div>
          ${topic ? `<div class="course-topic">Topic: ${escapeHtml(topic)}</div>` : ""}
          <div>Lecture Sec ${e.lecture.section} · ${e.lecture.meets_human || "TBA"}</div>
          ${e.lecture.instructor ? `<div>${e.lecture.instructor}</div>` : ""}
          ${e.recitation ? `<div>Recitation Sec ${e.recitation.section} · ${e.recitation.meets_human || "TBA"}</div>` : ""}
          ${e.lecture.school ? `<div style="color:#aaa;margin-top:2px">${e.lecture.school}</div>` : ""}
        </div>
      </div>`;
  }).join("");
}

function removeEntry(i) {
  schedule.splice(i, 1);
  saveSchedule();
  renderCalendar();
  renderSidebar();
}

function downloadCalendar() {
  if (schedule.length === 0) { alert("No courses in your schedule to export."); return; }

  // Detect term from schedule data, default to Fall 2026
  const termName = (schedule[0]?.lecture?.term || "Fall 2026").trim();
  const SEMESTERS = {
    "Spring 2026": { name: "Spring 2026", monday: [2026, 0, 26], until: "20260515T235959Z" },
    "Summer 2026": { name: "Summer 2026", monday: [2026, 4, 18], until: "20260814T235959Z" },
    "Fall 2026": { name: "Fall 2026", monday: [2026, 8, 7], until: "20261218T235959Z" },
  };
  const sem = SEMESTERS[termName] || SEMESTERS["Fall 2026"];
  const semMonday = new Date(sem.monday[0], sem.monday[1], sem.monday[2]);
  const DAY_CODES = ["MO", "TU", "WE", "TH", "FR"];

  function pad2(n) { return String(n).padStart(2, "0"); }
  function icsDate(d) { return `${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}`; }
  function icsTime(hhmm) { return hhmm.replace(":", "") + "00"; }
  function escape(s) {
    return (s || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
  }

  const lines = [
    "BEGIN:VCALENDAR", "VERSION:2.0",
    "PRODID:-//NYU Course Planner//EN", "CALSCALE:GREGORIAN",
    `X-WR-CALNAME:NYU ${sem.name} Schedule`, "X-WR-TIMEZONE:America/New_York",
  ];

  let uid = 0;
  schedule.forEach(({ lecture, recitation }) => {
    [lecture, recitation].filter(Boolean).forEach(sec => {
      (sec.meeting_times || []).forEach(mt => {
        if (!mt.start || !mt.end || typeof mt.day_num !== "number") return;
        if (mt.day_num < 0 || mt.day_num > 4) return;
        const firstDay = new Date(semMonday);
        firstDay.setDate(firstDay.getDate() + mt.day_num);
        const topic = topicText(sec);
        const summary = escape(`${sec.code}${sec.title ? " - " + sec.title : ""}${topic ? " - " + topic : ""}`);
        const desc = [
          topic ? `Topic: ${topic}` : "",
          sec.instructor ? `Instructor: ${sec.instructor}` : "",
          sec.component ? `Type: ${sec.component}` : "",
          sec.section ? `Section: ${sec.section}` : "",
          sec.crn ? `Class#: ${sec.crn}` : "",
        ].filter(Boolean).map(escape).join("\\n");
        lines.push(
          "BEGIN:VEVENT",
          `UID:nyu-${sec.crn}-${mt.day_num}-${++uid}@nyu-planner`,
          `SUMMARY:${summary}`,
          `DTSTART;TZID=America/New_York:${icsDate(firstDay)}T${icsTime(mt.start)}`,
          `DTEND;TZID=America/New_York:${icsDate(firstDay)}T${icsTime(mt.end)}`,
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

function clearAll() {
      if (!confirm("Clear your entire schedule?")) return;
      schedule = [];
      saveSchedule();
      renderCalendar();
      renderSidebar();
    }

renderCalendar();
  renderSidebar();

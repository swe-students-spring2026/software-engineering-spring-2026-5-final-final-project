const profileDataEl = document.getElementById('profile-data');
const profile = profileDataEl ? JSON.parse(profileDataEl.textContent || '{}') : (window.profile || {});
const completedSet = new Set((profile.completed_courses || []).map(c => normalizeCode(c)));
const currentSet   = new Set((profile.current_courses   || []).map(c => normalizeCode(c)));

// Build a normalized code → credit hours map from the transcript
const transcriptCredits = {};
Object.entries(profile.course_credits || {}).forEach(([code, credits]) => {
  transcriptCredits[normalizeCode(code)] = Number(credits) || 0;
});

function normalizeCode(s) {
  return (s || "").replace(/[-\s]+(\d{3}[-\s]\d{3}|\d{4}[-\s]\d{3})$/, "").trim().toUpperCase();
}

function canonicalRequirementCode(code) {
  const normalized = normalizeCode(code);
  const m = normalized.match(/^([A-Z]{2,5}-[A-Z]{2,3})\s+9(\d{3})$/);
  if (!m) return normalized;
  return `${m[1]} ${Number(m[2])}`;
}

const completedCanonicalSet = new Set([...completedSet].map(canonicalRequirementCode));
const currentCanonicalSet = new Set([...currentSet].map(canonicalRequirementCode));

function extractCode(cellText) {
  const cleaned = (cellText || "").replace(/^or\s+/i, "").trim();
  const m = cleaned.match(/^([A-Z]{2,5}-[A-Z]{2,3}[\s-]\d+)/i);
  return m ? m[1].replace(/-(\d)/, ' $1').trim().toUpperCase() : null;
}

function looksLikeCourseCode(s) {
  return /^(or\s+)?[A-Z]{2,5}[-][A-Z]{2,3}[\s\/]/i.test(s || "");
}

function isSamplePlan(label) {
  return /sample|plan|semester|term/i.test(label || "");
}

function statusOf(code) {
  if (!code) return "none";
  const n = canonicalRequirementCode(code);
  if (completedCanonicalSet.has(n)) return "done";
  if (currentCanonicalSet.has(n))   return "current";
  return "needed";
}

function parseCredits(value) {
  const matches = String(value || "").match(/\d+(?:\.\d+)?/g);
  if (!matches || !matches.length) return 0;
  return Math.max(...matches.map(Number));
}

function formatCredits(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, "");
}

const specialRequirements = [
  {
    key: "texts-ideas",
    label: "Texts & Ideas",
    match: text => /^texts\s*&\s*ideas$/i.test(text || ""),
    options: ["CORE-UA 400 through CORE-UA 499", "Global-site equivalents CORE-UA 9400 through CORE-UA 9499"],
    matches: code => {
      const m = canonicalRequirementCode(code).match(/^CORE-UA\s+(\d+)$/);
      return !!m && Number(m[1]) >= 400 && Number(m[1]) <= 499;
    },
  },
  {
    key: "cultures-contexts-global-cultures",
    label: "Cultures & Contexts, or Global Cultures",
    match: text => /cultures\s*&\s*contexts/i.test(text || "") && /global\s+cultures/i.test(text || ""),
    options: ["CORE-UA 500 through CORE-UA 599", "Global-site equivalents CORE-UA 9500 through CORE-UA 9599", "Any Global Cultures course ending in GC-UF 101", "Global-site Global Cultures equivalents ending in GC-UF 9101"],
    matches: code => {
      const normalized = canonicalRequirementCode(code);
      const core = normalized.match(/^CORE-UA\s+(\d+)$/);
      if (core && Number(core[1]) >= 500 && Number(core[1]) <= 599) return true;
      return /^[A-Z]+GC-UF\s+101$/.test(normalized);
    },
  },
];

function findSpecialRequirement(first) {
  return specialRequirements.find(req => req.match(first));
}

function statusOfSpecialRequirement(req) {
  if ([...completedCanonicalSet].some(code => req.matches(code))) return "done";
  if ([...currentCanonicalSet].some(code => req.matches(code))) return "current";
  return "needed";
}

function renderSpecialRequirementOptions(req) {
  const completedMatches = [...completedCanonicalSet].filter(code => req.matches(code));
  const currentMatches = [...currentCanonicalSet].filter(code => req.matches(code));
  const matches = [
    ...completedMatches.map(code => `Completed: ${code}`),
    ...currentMatches.map(code => `In progress: ${code}`),
  ];
  return `
    <details class="choice-options">
      <summary>Accepted courses</summary>
      <table>
        <tbody>
          ${req.options.map(option => `<tr><td colspan="4">${option}</td></tr>`).join("")}
          ${matches.map(match => `<tr class="row-done"><td colspan="4">${match}</td></tr>`).join("")}
        </tbody>
      </table>
    </details>`;
}

function choiceKey(value) {
  return (value || "")
    .toLowerCase()
    .replace(/\brequirements?\b/g, "")
    .replace(/\bselect\s+one\b/g, "")
    .replace(/\bby\s+advisement\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function buildChoiceTables(tables) {
  const choices = new Map();
  tables.forEach(t => {
    const label = t.label || "";
    if (!/elective/i.test(label) || !/requirement/i.test(label)) return;
    const options = (t.rows || [])
      .map(row => {
        const cells = row || [];
        const first = (cells[0] || "").trim();
        const code = extractCode(first);
        return code ? { code, display: first, title: cells[1] || "", credits: cells[2] || "" } : null;
      })
      .filter(Boolean);
    if (options.length) choices.set(choiceKey(label), { label, options });
  });
  return choices;
}

function isChoiceTable(t, choiceTables) {
  return choiceTables.has(choiceKey(t.label || ""));
}

function choiceRequirementKey(text) {
  const cleaned = (text || "").replace(/^select\s+one\s+/i, "");
  return choiceKey(cleaned);
}

function findChoiceRequirement(first, choiceTables) {
  if (!/^select\s+one\b/i.test(first || "")) return null;
  const key = choiceRequirementKey(first);
  if (choiceTables.has(key)) return choiceTables.get(key);

  for (const [choiceKeyValue, choice] of choiceTables.entries()) {
    if (key.includes(choiceKeyValue) || choiceKeyValue.includes(key)) return choice;
  }
  return null;
}

function statusOfChoice(options) {
  if (options.some(option => statusOf(option.code) === "done")) return "done";
  if (options.some(option => statusOf(option.code) === "current")) return "current";
  return "needed";
}

function matchedChoiceOption(options) {
  return options.find(option => statusOf(option.code) === "done")
      || options.find(option => statusOf(option.code) === "current")
      || null;
}

function choiceOptionKey(option) {
  return canonicalRequirementCode(option?.code || "");
}

function creditsForChoice(options, fallbackCredits) {
  const matched = matchedChoiceOption(options);
  if (matched?.code) {
    const tc = transcriptCredits[normalizeCode(matched.code)];
    if (tc !== undefined) return tc;
  }
  return parseCredits(matched?.credits || fallbackCredits);
}

function extraChoiceCredits(choiceTables, creditedChoiceKeys) {
  let doneCredits = 0;
  let currentCredits = 0;

  for (const choice of choiceTables.values()) {
    choice.options.forEach(option => {
      const key = choiceOptionKey(option);
      const st = statusOf(option.code);
      if (!key || creditedChoiceKeys.has(key)) return;
      if (st !== "done" && st !== "current") return;

      const credits = parseCredits(option.credits);
      if (st === "done") doneCredits += credits;
      else currentCredits += credits;
      creditedChoiceKeys.add(key);
    });
  }

  return { doneCredits, currentCredits };
}

function renderChoiceOptions(choice) {
  const rows = choice.options.map(option => {
    const st = statusOf(option.code);
    const icon = st === "done"    ? '<span class="status-icon status-done">✓</span>'
                 : st === "current" ? '<span class="status-icon status-current">→</span>'
                 :                    '<span class="status-icon status-needed">○</span>';
    const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
    return `<tr class="${rowCls}"><td>${icon}</td><td><span class="course-code">${option.display}</span></td><td>${option.title}</td><td>${option.credits}</td></tr>`;
  }).join("");
  return `
    <details class="choice-options">
      <summary>Elective options</summary>
      <table>
        <thead><tr><th style="width:28px"></th><th>Course</th><th>Title</th><th>Credits</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </details>`;
}

function renderTable(t, choiceTables, creditedChoiceKeys) {
  const rows = t.rows || [];
  let doneCnt = 0, currentCnt = 0, neededCnt = 0;
  let doneCredits = 0, currentCredits = 0, requiredCredits = 0;
  let tableHtml = `<table><thead><tr><th style="width:28px"></th><th>Course</th><th>Title</th><th>Credits</th></tr></thead><tbody>`;

  rows.forEach(row => {
    const cells = row || [];
    const first = (cells[0] || "").trim();
    const isCourse = looksLikeCourseCode(first);
    const isAlt    = first.toLowerCase().startsWith("or ");
    const isTotal  = /total\s+credits/i.test(first);
    const choice = findChoiceRequirement(first, choiceTables);
    const specialReq = findSpecialRequirement(first);

    if (isTotal) {
      const totalCredits = parseCredits(cells[1] || cells[2]);
      if (totalCredits) requiredCredits = Math.max(requiredCredits, totalCredits);
      tableHtml += `<tr class="total-row"><td></td><td colspan="2">${first}</td><td>${formatCredits(doneCredits + currentCredits)} / ${cells[1] || cells[2] || ""}</td></tr>`;
      return;
    }
    if (specialReq) {
      const st = statusOfSpecialRequirement(specialReq);
      const credits = parseCredits(cells[1]);
      if      (st === "done")    doneCnt++;
      else if (st === "current") currentCnt++;
      else                       neededCnt++;
      if      (st === "done")    doneCredits += credits;
      else if (st === "current") currentCredits += credits;

      const icon = st === "done"    ? '<span class="status-icon status-done">✓</span>'
                 : st === "current" ? '<span class="status-icon status-current">→</span>'
                 :                    '<span class="status-icon status-needed">○</span>';
      const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
      tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td colspan="2"><span class="choice-label">${first}</span></td><td>${cells[1] || ""}</td></tr>`;
      tableHtml += `<tr class="choice-options-row"><td></td><td colspan="3">${renderSpecialRequirementOptions(specialReq)}</td></tr>`;
      return;
    }
    if (choice) {
      const st = statusOfChoice(choice.options);
      const matched = matchedChoiceOption(choice.options);
      const credits = creditsForChoice(choice.options, cells[1]);
      if      (st === "done")    doneCnt++;
      else if (st === "current") currentCnt++;
      else                       neededCnt++;
      if      (st === "done")    doneCredits += credits;
      else if (st === "current") currentCredits += credits;
      if (matched && (st === "done" || st === "current")) {
        creditedChoiceKeys.add(choiceOptionKey(matched));
      }

      const icon = st === "done"    ? '<span class="status-icon status-done">✓</span>'
                 : st === "current" ? '<span class="status-icon status-current">→</span>'
                 :                    '<span class="status-icon status-needed">○</span>';
      const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
      tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td colspan="2"><span class="choice-label">${first}</span></td><td>${cells[1] || ""}</td></tr>`;
      tableHtml += `<tr class="choice-options-row"><td></td><td colspan="3">${renderChoiceOptions(choice)}</td></tr>`;
      return;
    }
    if (!isCourse && !isAlt) {
      // "Other Elective Credits" — count unmatched completed courses toward it
      if (/other\s+elective/i.test(first)) {
        const unmatched = [...completedSet].filter(c => !creditedChoiceKeys.has(canonicalRequirementCode(c)));
        const unmatchedCredits = unmatched.length * 4; // approximate; exact credits need DB lookup
        const st = unmatched.length > 0 ? "done" : "needed";
        const icon = st === "done" ? '<span class="status-icon status-done">✓</span>' : '<span class="status-icon status-needed">○</span>';
        const rowCls = st === "done" ? "row-done" : "";
        const creditDisplay = unmatched.length > 0 ? `${unmatchedCredits}+ / ${cells[1] || ""}` : (cells[1] || "");
        tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td colspan="2">${first}${unmatched.length > 0 ? ` <span style="font-size:0.75rem;color:#555;font-weight:normal">(${unmatched.length} extra courses)</span>` : ""}</td><td>${creditDisplay}</td></tr>`;
      } else {
        tableHtml += `<tr class="group-row"><td></td><td colspan="2">${first}</td><td>${cells[1] || ""}</td></tr>`;
      }
      return;
    }

    const code = extractCode(first);
    const st = statusOf(code);
    // credits: transcript value first, then bulletin (cells[2] or cells[1] for 2-col rows)
    const creditVal = cells[2] !== undefined ? cells[2] : (cells.length === 2 ? cells[1] : "");
    const transcriptCredit = code ? transcriptCredits[normalizeCode(code)] : undefined;
    const credits = transcriptCredit !== undefined ? transcriptCredit : parseCredits(creditVal);
    if      (st === "done")    doneCnt++;
    else if (st === "current") currentCnt++;
    else if (code)             neededCnt++;
    if      (st === "done")    doneCredits += credits;
    else if (st === "current") currentCredits += credits;

    const icon = st === "done"    ? '<span class="status-icon status-done">✓</span>'
               : st === "current" ? '<span class="status-icon status-current">→</span>'
               :                    '<span class="status-icon status-needed">○</span>';
    const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
    if (code && (st === "done" || st === "current")) {
      creditedChoiceKeys.add(canonicalRequirementCode(code));
    }
    const altCls = isAlt ? " alt-row" : "";
    const codeHtml = code ? `<span class="course-code">${first}</span>` : first;
    tableHtml += `<tr class="${rowCls}${altCls}"><td>${icon}</td><td>${codeHtml}</td><td>${cells[1] || ""}</td><td>${creditVal}</td></tr>`;
  });

  tableHtml += `</tbody></table>`;
  return { html: tableHtml, done: doneCnt, current: currentCnt, needed: neededCnt, doneCredits, currentCredits, requiredCredits };
}

async function render() {
  const root = document.getElementById("page-root");
  const majorUrl = profile.major_url;

  if (!majorUrl) {
    root.innerHTML = `
      <div class="no-major">
        <h2>No major selected</h2>
        <p>Go to your profile settings and select your school and major to see graduation requirements.</p>
        <a href="/profile" class="btn">Go to Settings</a>
      </div>`;
    return;
  }

  let prog;
  try {
    const res = await fetch(`/api/program-requirements?url=${encodeURIComponent(majorUrl)}`);
    prog = await res.json();
    if (!res.ok) throw new Error(prog.error || "Failed to load");
  } catch (e) {
    root.innerHTML = `<div class="loading">Error loading requirements: ${e.message}</div>`;
    return;
  }

  const allTables = (prog.tables || []).filter(t => !isSamplePlan(t.label));
  const choiceTables = buildChoiceTables(allTables);
  const tables = allTables.filter(t => !isChoiceTable(t, choiceTables));
  const creditedChoiceKeys = new Set();
  let totalDone = 0, totalCurrent = 0, totalNeeded = 0;
  let totalDoneCredits = 0, totalCurrentCredits = 0, totalRequiredCredits = 0;
  const renderedSections = tables.map(t => {
    const r = renderTable(t, choiceTables, creditedChoiceKeys);
    totalDone    += r.done;
    totalCurrent += r.current;
    totalNeeded  += r.needed;
    totalDoneCredits += r.doneCredits;
    totalCurrentCredits += r.currentCredits;
    totalRequiredCredits = Math.max(totalRequiredCredits, r.requiredCredits || 0);
    return { label: t.label || "Requirements", ...r };
  });
  const extraCredits = extraChoiceCredits(choiceTables, creditedChoiceKeys);
  totalDoneCredits += extraCredits.doneCredits;
  totalCurrentCredits += extraCredits.currentCredits;

  const totalCourses = totalDone + totalCurrent + totalNeeded;
  const pct = totalCourses ? Math.round((totalDone / totalCourses) * 100) : 0;

  let html = `
    <div class="summary-card">
      <div class="summary-info">
        <h2>${prog.title || "Graduation Progress"}</h2>
        <div class="sub">${prog.school || ""}${profile.minor ? " · Minor: " + profile.minor : ""}</div>
        <div class="stat-pills">
          <span class="pill pill-done">✓ ${totalDone} completed</span>
          ${totalCurrent ? `<span class="pill pill-current">→ ${totalCurrent} in progress</span>` : ""}
          <span class="pill pill-needed">○ ${totalNeeded} remaining</span>
          ${totalRequiredCredits ? `<span class="pill pill-done">${formatCredits(totalDoneCredits + totalCurrentCredits)} / ${formatCredits(totalRequiredCredits)} credits</span>` : ""}
        </div>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-label"><span>Overall completion</span><span>${pct}%</span></div>
        <div class="progress-bar-track"><div class="progress-bar-fill" style="width:${pct}%"></div></div>
      </div>
    </div>

    <div class="legend">
      <span class="legend-item"><span class="dot" style="background:#28a745"></span> Completed</span>
      <span class="legend-item"><span class="dot" style="background:#0369a1"></span> Currently enrolled</span>
      <span class="legend-item"><span class="dot" style="background:#ccc"></span> Not yet taken</span>
    </div>`;

  renderedSections.forEach((sec, i) => {
    const badge = sec.done
      ? `<span class="pill pill-done" style="font-size:0.72rem">${sec.done}/${sec.done + sec.current + sec.needed}</span>`
      : "";
    html += `
      <div class="req-section" id="sec-${i}">
        <div class="req-section-header" onclick="toggleSection('sec-${i}')">
          <h3>${sec.label}</h3>
          <div class="sec-stats">${badge}<span class="chevron">▾</span></div>
        </div>
        <div class="req-section-body">${sec.html}</div>
      </div>`;
  });

  root.innerHTML = html;
}

function toggleSection(id) {
  document.getElementById(id).classList.toggle("collapsed");
}

render();

const profileDataEl = document.getElementById('profile-data');
const profile = profileDataEl ? JSON.parse(profileDataEl.textContent || '{}') : (window.profile || {});
const completedSet = new Set((profile.completed_courses || []).map(c => normalizeCode(c)).filter(isTranscriptCourseCode));
const currentSet = new Set((profile.current_courses || []).map(c => normalizeCode(c)).filter(isTranscriptCourseCode));

// Build a normalized code → credit hours map from the transcript
const transcriptCredits = {};
Object.entries(profile.course_credits || {}).forEach(([code, credits]) => {
    const normalized = normalizeCode(code);
    if (isTranscriptCourseCode(normalized)) {
        transcriptCredits[normalized] = toCreditNumber(credits);
    }
});
const courseCatalogCredits = {};

const testCredits = (profile.test_credits || [])
    .map(credit => ({
        test: String(credit?.test || "Test").trim(),
        component: String(credit?.component || "").trim(),
        units: toCreditNumber(credit?.units),
    }))
    .filter(credit => credit.units > 0);
const testCreditEntryTotal = testCredits.reduce((total, credit) => total + credit.units, 0);
const testCreditTotal = testCredits.length ? testCreditEntryTotal : toCreditNumber(profile.test_credit_total);

function normalizeCode(s) {
    return (s || "").replace(/[-\s]+(\d{3}[-\s]\d{3}|\d{4}[-\s]\d{3})$/, "").trim().toUpperCase();
}

function isTranscriptCourseCode(s) {
    return /^[A-Z]{2,5}-[A-Z]{2,3}\s+\d+[A-Z]?$/i.test(s || "");
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
    if (currentCanonicalSet.has(n)) return "current";
    return "needed";
}

function parseCredits(value) {
    const matches = String(value || "").match(/\d+(?:\.\d+)?/g);
    if (!matches || !matches.length) return 0;
    return Math.max(...matches.map(Number));
}

function toCreditNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

function hasExplicitCreditValue(value) {
    return String(value ?? "").trim() !== "";
}

function formatCredits(value) {
    return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(/\.0$/, "");
}

function hasTranscriptCredit(code) {
    return transcriptCredits[normalizeCode(code)] !== undefined;
}

function hasCatalogCredit(code) {
    return courseCatalogCredits[normalizeCode(code)] !== undefined;
}

function creditsForCourse(code, fallbackCredits = 0) {
    const normalized = normalizeCode(code);
    if (transcriptCredits[normalized] !== undefined) return transcriptCredits[normalized];
    if (courseCatalogCredits[normalized] !== undefined) return courseCatalogCredits[normalized];
    return fallbackCredits;
}

function displayCreditsForCourse(code, fallbackValue = "") {
    const normalized = normalizeCode(code);
    if (transcriptCredits[normalized] !== undefined) return formatCredits(transcriptCredits[normalized]);
    if (courseCatalogCredits[normalized] !== undefined) return formatCredits(courseCatalogCredits[normalized]);
    return fallbackValue || "";
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
    {
        key: "language-expository",
        label: "Language / Expository Writing",
        match: text => /language|expository\s+writing|expos/i.test(text || ""),
        resolve: first => {
            const text = String(first || "");
            const onlyNine = /(?:\bonly\s*9\b|\b9\s*only\b|EXPOS-UA\s*9\s*only)/i.test(text);
            const fourAndNine = /(?:\b4\s*(?:and|&|\/|to)\s*9\b|EXPOS-UA\s*4.*EXPOS-UA\s*9|EXPOS-UA\s*9.*EXPOS-UA\s*4)/i.test(text);
            const options = onlyNine
                ? ["EXPOS-UA 9"]
                : fourAndNine
                    ? ["EXPOS-UA 4", "EXPOS-UA 9"]
                    : ["EXPOS-UA 4", "EXPOS-UA 9"];

            return {
                key: "language-expository",
                label: "Language / Expository Writing",
                options,
                matches: code => options.some(option => canonicalRequirementCode(code) === canonicalRequirementCode(option)),
            };
        },
    },
    {
        key: "first-year-seminar",
        label: "First-Year Seminar",
        match: text => /first[\s-]*year.*seminar/i.test(text || ""),
        options: ["FYSEM-UA 1", "FYSEM-UA 2"],
        matches: code => {
            const normalized = canonicalRequirementCode(code);
            return /^FYSEM-UA\s+\d+/i.test(normalized);
        },
    },
];

function findSpecialRequirement(first) {
    const req = specialRequirements.find(entry => entry.match(first));
    if (!req) return null;
    return typeof req.resolve === "function" ? req.resolve(first) : req;
}

function matchedSpecialRequirementCourse(req, sourceSet = completedSet) {
    return [...sourceSet].find(code => req.matches(code)) || null;
}

function statusOfSpecialRequirement(req) {
    if (matchedSpecialRequirementCourse(req, completedSet)) return "done";
    if (matchedSpecialRequirementCourse(req, currentSet)) return "current";
    return "needed";
}

function renderSpecialRequirementOptions(req) {
    const completedMatches = [...completedSet].filter(code => req.matches(code));
    const currentMatches = [...currentSet].filter(code => req.matches(code));
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
    const key = choiceRequirementKey(first);
    if (/^select\s+one\b/i.test(first || "")) {
        if (choiceTables.has(key)) return choiceTables.get(key);

        for (const [choiceKeyValue, choice] of choiceTables.entries()) {
            if (key.includes(choiceKeyValue) || choiceKeyValue.includes(key)) return choice;
        }
    }

    return parseInlineChoiceRequirement(first);
}

function parseInlineChoiceRequirement(first) {
    const cleaned = (first || "").replace(/^select\s+one\s+/i, "").trim();
    if (!cleaned) return null;

    const codes = [...new Set((cleaned.match(/[A-Z]{2,5}-[A-Z]{2,3}[\s-]\d+[A-Z]?/gi) || [])
        .map(code => extractCode(code))
        .filter(Boolean))];

    if (codes.length < 2) return null;

    return {
        label: cleaned,
        options: codes.map(code => ({ code, display: code, title: "", credits: "" })),
    };
}

function parseWildcardElectivePrefix(first) {
    const cleaned = (first || "").trim();
    const match = cleaned.match(/^([A-Z]{2,5}-[A-Z]{2,3})\s+[-_Xx•.]{2,}$/);
    return match ? match[1].toUpperCase() : null;
}

function matchWildcardElectiveCourse(prefix, assignedCourseCodes) {
    const isEligible = code => {
        const normalized = canonicalRequirementCode(code);
        return normalized.startsWith(`${prefix} `) && !assignedCourseCodes.has(normalized);
    };

    const completedMatch = [...completedSet].find(isEligible);
    if (completedMatch) return completedMatch;

    return [...currentSet].find(isEligible) || null;
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
        return creditsForCourse(matched.code, parseCredits(matched.credits || fallbackCredits));
    }
    return parseCredits(matched?.credits || fallbackCredits);
}

function creditsForTranscriptCode(code, fallbackCredits = 0) {
    return creditsForCourse(code, fallbackCredits);
}

function sumTranscriptCredits(codes, fallbackCredits = 0) {
    return codes.reduce((total, code) => total + creditsForTranscriptCode(code, fallbackCredits), 0);
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function collectSatisfiedRequirementKeys(tables, choiceTables) {
    const keys = new Set();
    tables.forEach(t => {
        (t.rows || []).forEach(row => {
            const cells = row || [];
            const first = (cells[0] || "").trim();
            const isCourse = looksLikeCourseCode(first);
            const isAlt = first.toLowerCase().startsWith("or ");
            const choice = findChoiceRequirement(first, choiceTables);
            const specialReq = findSpecialRequirement(first);

            if (specialReq) {
                const matched = matchedSpecialRequirementCourse(specialReq, completedSet)
                    || matchedSpecialRequirementCourse(specialReq, currentSet);
                if (matched) keys.add(canonicalRequirementCode(matched));
                return;
            }
            if (choice) {
                const matched = matchedChoiceOption(choice.options);
                if (matched && statusOf(matched.code) !== "needed") {
                    keys.add(choiceOptionKey(matched));
                }
                return;
            }
            if (!isCourse && !isAlt) return;

            const code = extractCode(first);
            if (code && statusOf(code) !== "needed") {
                keys.add(canonicalRequirementCode(code));
            }
        });
    });
    return keys;
}

function collectCourseCreditLookupCodes(tables, choiceTables) {
    const codes = new Set();
    const maybeAdd = (code, fallbackValue = "") => {
        if (!code || hasTranscriptCredit(code)) return;
        if (!hasExplicitCreditValue(fallbackValue)) codes.add(normalizeCode(code));
    };

    tables.forEach(t => {
        (t.rows || []).forEach(row => {
            const cells = row || [];
            const first = (cells[0] || "").trim();
            const isCourse = looksLikeCourseCode(first);
            const isAlt = first.toLowerCase().startsWith("or ");
            const choice = findChoiceRequirement(first, choiceTables);

            if (choice) {
                choice.options.forEach(option => maybeAdd(option.code, option.credits));
                return;
            }
            if (!isCourse && !isAlt) return;

            const code = extractCode(first);
            const creditVal = cells[2] !== undefined ? cells[2] : (cells.length === 2 ? cells[1] : "");
            maybeAdd(code, creditVal);
        });
    });

    [...completedSet, ...currentSet].forEach(code => maybeAdd(code));
    return codes;
}

async function loadCourseCatalogCredits(codes) {
    const missingCodes = [...codes].filter(code => code && !hasTranscriptCredit(code) && !hasCatalogCredit(code));
    await Promise.all(missingCodes.map(async code => {
        const credits = await fetchCourseCatalogCredits(code);
        if (credits !== null) {
            courseCatalogCredits[normalizeCode(code)] = credits;
        }
    }));
}

async function fetchCourseCatalogCredits(code) {
    for (const source of ["bulletin", "albert"]) {
        try {
            const res = await fetch(`/api/classes?source=${source}&q=${encodeURIComponent(code)}`);
            if (!res.ok) continue;
            const payload = await res.json();
            const classes = Array.isArray(payload.classes) ? payload.classes : [];
            const exact = classes.find(course => canonicalRequirementCode(course.code) === canonicalRequirementCode(code))
                || classes.find(course => normalizeCode(course.code) === normalizeCode(code));
            if (!exact) continue;
            const rawCredits = exact.credits ?? exact.units ?? "";
            if (!hasExplicitCreditValue(rawCredits)) continue;
            return parseCredits(rawCredits);
        } catch (err) {
            // Missing catalog credits should not block rendering transcript-backed progress.
        }
    }
    return null;
}

function electiveCreditBreakdown(creditedRequirementKeys) {
    const isOutsideRequirement = code => !creditedRequirementKeys.has(canonicalRequirementCode(code));
    const completedOutside = [...completedSet].filter(isOutsideRequirement);
    const currentOutside = [...currentSet].filter(isOutsideRequirement);
    const completedCourseCredits = sumTranscriptCredits(completedOutside);
    const currentCourseCredits = sumTranscriptCredits(currentOutside);

    return {
        completedOutside,
        currentOutside,
        completedCourseCredits,
        currentCourseCredits,
        testCreditTotal,
        earnedCredits: completedCourseCredits + testCreditTotal,
        totalCredits: completedCourseCredits + currentCourseCredits + testCreditTotal,
    };
}

function renderAppliedElectiveCreditsDetails(breakdown) {
    const rows = [];
    const courseCount = breakdown.completedOutside.length + breakdown.currentOutside.length;
    const courseCredits = breakdown.completedCourseCredits + breakdown.currentCourseCredits;

    if (courseCredits > 0 || courseCount > 0) {
        rows.push(`
            <tr class="elective-detail-group">
              <td></td><td colspan="2">Courses Outside Requirements <span class="credit-note">(${courseCount} courses)</span></td><td>${formatCredits(courseCredits)}</td>
            </tr>`);
        breakdown.completedOutside.forEach(code => {
            rows.push(`
                <tr class="row-done">
                  <td><span class="status-icon status-done">&#10003;</span></td>
                  <td><span class="course-code">${escapeHtml(code)}</span></td>
                  <td>Completed outside requirements</td>
                  <td>${formatCredits(creditsForTranscriptCode(code))}</td>
                </tr>`);
        });
        breakdown.currentOutside.forEach(code => {
            rows.push(`
                <tr class="row-current">
                  <td><span class="status-icon status-current">&rarr;</span></td>
                  <td><span class="course-code">${escapeHtml(code)}</span></td>
                  <td>In progress outside requirements</td>
                  <td>${formatCredits(creditsForTranscriptCode(code))}</td>
                </tr>`);
        });
    }

    if (breakdown.testCreditTotal > 0) {
        rows.push(`
            <tr class="elective-detail-group">
              <td></td><td colspan="2">AP/IB/Test Credits</td><td>${formatCredits(breakdown.testCreditTotal)}</td>
            </tr>`);
        testCredits.forEach(credit => {
            rows.push(`
                <tr class="row-done">
                  <td><span class="status-icon status-done">&#10003;</span></td>
                  <td><span class="course-code">${escapeHtml(credit.test)}</span></td>
                  <td>${escapeHtml(credit.component)}</td>
                  <td>${formatCredits(credit.units)}</td>
                </tr>`);
        });
    }

    if (!rows.length) return "";
    return `
    <details class="choice-options elective-credit-options">
      <summary>Applied elective credits</summary>
      <table>
        <thead><tr><th style="width:28px"></th><th>Credit</th><th>For</th><th>Credits</th></tr></thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </details>`;
}

function renderElectiveCreditBreakdownRows(breakdown) {
    const details = renderAppliedElectiveCreditsDetails(breakdown);
    if (!details) return "";
    return `<tr class="choice-options-row elective-credit-options-row"><td></td><td colspan="3">${details}</td></tr>`;
}

function renderStandaloneTestCreditsSection() {
    if (testCreditTotal <= 0) return null;
    const rows = testCredits.length
        ? testCredits.map(credit => `
            <tr class="row-done">
              <td><span class="status-icon status-done">&#10003;</span></td>
              <td><span class="course-code">${escapeHtml(credit.test)}</span></td>
              <td>${escapeHtml(credit.component || "Applied AP/IB/Test credit")}</td>
              <td>${formatCredits(credit.units)}</td>
            </tr>`).join("")
        : `
            <tr class="row-done">
              <td><span class="status-icon status-done">&#10003;</span></td>
              <td><span class="course-code">TEST CREDIT</span></td>
              <td>Applied AP/IB/Test credits from transcript</td>
              <td>${formatCredits(testCreditTotal)}</td>
            </tr>`;
    return {
        label: "Applied AP/IB/Test Credits",
        html: `
            <table>
              <thead><tr><th style="width:28px"></th><th>Credit</th><th>For</th><th>Credits</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>`,
        done: testCredits.length || 1,
        current: 0,
        needed: 0,
        doneCredits: testCreditTotal,
        currentCredits: 0,
        requiredCredits: 0,
    };
}

function renderChoiceOptions(choice) {
    const rows = choice.options.map(option => {
        const st = statusOf(option.code);
        const icon = st === "done" ? '<span class="status-icon status-done">✓</span>'
            : st === "current" ? '<span class="status-icon status-current">→</span>'
                : '<span class="status-icon status-needed">○</span>';
        const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
        const creditDisplay = displayCreditsForCourse(option.code, option.credits);
        return `<tr class="${rowCls}"><td>${icon}</td><td><span class="course-code">${option.display}</span></td><td>${option.title}</td><td>${creditDisplay}</td></tr>`;
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

function renderTable(t, choiceTables, creditedRequirementKeys, assignedElectiveCourseCodes = new Set()) {
    const rows = t.rows || [];
    let doneCnt = 0, currentCnt = 0, neededCnt = 0;
    let doneCredits = 0, currentCredits = 0, requiredCredits = 0;
    let tableHtml = `<table><thead><tr><th style="width:28px"></th><th>Course</th><th>Title</th><th>Credits</th></tr></thead><tbody>`;

    rows.forEach(row => {
        const cells = row || [];
        const first = (cells[0] || "").trim();
        const isCourse = looksLikeCourseCode(first);
        const isAlt = first.toLowerCase().startsWith("or ");
        const isTotal = /total\s+credits/i.test(first);
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
            if (st === "done") doneCnt++;
            else if (st === "current") currentCnt++;
            else neededCnt++;
            if (st === "done") doneCredits += credits;
            else if (st === "current") currentCredits += credits;

            const icon = st === "done" ? '<span class="status-icon status-done">✓</span>'
                : st === "current" ? '<span class="status-icon status-current">→</span>'
                    : '<span class="status-icon status-needed">○</span>';
            const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
            tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td colspan="2"><span class="choice-label">${first}</span></td><td>${cells[1] || ""}</td></tr>`;
            tableHtml += `<tr class="choice-options-row"><td></td><td colspan="3">${renderSpecialRequirementOptions(specialReq)}</td></tr>`;
            const matched = matchedSpecialRequirementCourse(specialReq, completedSet)
                || matchedSpecialRequirementCourse(specialReq, currentSet);
            if (matched && (st === "done" || st === "current")) {
                creditedRequirementKeys.add(canonicalRequirementCode(matched));
            }
            return;
        }
        if (choice) {
            const st = statusOfChoice(choice.options);
            const matched = matchedChoiceOption(choice.options);
            const credits = creditsForChoice(choice.options, cells[1]);
            if (st === "done") doneCnt++;
            else if (st === "current") currentCnt++;
            else neededCnt++;
            if (st === "done") doneCredits += credits;
            else if (st === "current") currentCredits += credits;
            if (matched && (st === "done" || st === "current")) {
                creditedRequirementKeys.add(choiceOptionKey(matched));
            }

            const icon = st === "done" ? '<span class="status-icon status-done">✓</span>'
                : st === "current" ? '<span class="status-icon status-current">→</span>'
                    : '<span class="status-icon status-needed">○</span>';
            const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
            tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td colspan="2"><span class="choice-label">${first}</span></td><td>${cells[1] || ""}</td></tr>`;
            tableHtml += `<tr class="choice-options-row"><td></td><td colspan="3">${renderChoiceOptions(choice)}</td></tr>`;
            return;
        }
        const wildcardElectivePrefix = parseWildcardElectivePrefix(first);
        if (wildcardElectivePrefix) {
            const matched = matchWildcardElectiveCourse(wildcardElectivePrefix, assignedElectiveCourseCodes);
            const creditVal = cells[2] !== undefined ? cells[2] : (cells.length === 2 ? cells[1] : "");
            const credits = matched ? creditsForCourse(matched, parseCredits(creditVal)) : parseCredits(creditVal);
            const st = matched ? statusOf(matched) : (parseCredits(creditVal) > 0 ? "needed" : "none");
            if (matched) {
                assignedElectiveCourseCodes.add(canonicalRequirementCode(matched));
                creditedRequirementKeys.add(canonicalRequirementCode(matched));
            }

            if (st === "done") doneCnt++;
            else if (st === "current") currentCnt++;
            else neededCnt++;
            if (st === "done") doneCredits += credits;
            else if (st === "current") currentCredits += credits;

            const icon = st === "done" ? '<span class="status-icon status-done">✓</span>'
                : st === "current" ? '<span class="status-icon status-current">→</span>'
                    : '<span class="status-icon status-needed">○</span>';
            const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
            const codeHtml = matched ? `<span class="course-code">${escapeHtml(matched)}</span>` : `<span class="course-code">${first}</span>`;
            const creditDisplay = matched ? displayCreditsForCourse(matched, creditVal) : creditVal;

            tableHtml += `<tr class="${rowCls}"><td>${icon}</td><td>${codeHtml}</td><td>${cells[1] || ""}</td><td>${creditDisplay}</td></tr>`;
            return;
        }
        if (!isCourse && !isAlt) {
            // "Other Elective Credits" — count unmatched completed courses toward it
            if (/other\s+elective/i.test(first)) {
                const breakdown = electiveCreditBreakdown(creditedRequirementKeys);
                const requirementCredits = parseCredits(cells[1] || cells[2]);
                const appliedDoneCredits = requirementCredits
                    ? Math.min(breakdown.earnedCredits, requirementCredits)
                    : breakdown.earnedCredits;
                const remainingAfterDone = requirementCredits ? Math.max(requirementCredits - appliedDoneCredits, 0) : 0;
                const appliedCurrentCredits = requirementCredits
                    ? Math.min(breakdown.currentCourseCredits, remainingAfterDone)
                    : breakdown.currentCourseCredits;
                const appliedCredits = appliedDoneCredits + appliedCurrentCredits;
                const st = requirementCredits && appliedCredits >= requirementCredits
                    ? "done"
                    : appliedCredits > 0 ? "current" : "needed";
                const icon = st === "done" ? '<span class="status-icon status-done">✓</span>' : '<span class="status-icon status-needed">○</span>';
                const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
                const displayIcon = st === "done" ? '<span class="status-icon status-done">&#10003;</span>'
                    : st === "current" ? '<span class="status-icon status-current">&rarr;</span>'
                        : '<span class="status-icon status-needed">&#9675;</span>';
                const creditDisplay = requirementCredits
                    ? `${formatCredits(appliedCredits)} / ${formatCredits(requirementCredits)}`
                    : formatCredits(appliedCredits);
                if (st === "done") doneCnt++;
                else if (st === "current") currentCnt++;
                else neededCnt++;
                doneCredits += appliedDoneCredits;
                currentCredits += appliedCurrentCredits;

                tableHtml += `<tr class="${rowCls}"><td>${displayIcon}</td><td colspan="2">${first}</td><td>${creditDisplay}</td></tr>`;
                tableHtml += renderElectiveCreditBreakdownRows(breakdown);
            } else {
                tableHtml += `<tr class="group-row"><td></td><td colspan="2">${first}</td><td>${cells[1] || ""}</td></tr>`;
            }
            return;
        }

        const code = extractCode(first);
        const st = statusOf(code);
        // credits: transcript value first, then bulletin (cells[2] or cells[1] for 2-col rows)
        const creditVal = cells[2] !== undefined ? cells[2] : (cells.length === 2 ? cells[1] : "");
        const credits = code ? creditsForCourse(code, parseCredits(creditVal)) : parseCredits(creditVal);
        const creditDisplay = code ? displayCreditsForCourse(code, creditVal) : creditVal;
        if (st === "done") doneCnt++;
        else if (st === "current") currentCnt++;
        else if (code) neededCnt++;
        if (st === "done") doneCredits += credits;
        else if (st === "current") currentCredits += credits;

        const icon = st === "done" ? '<span class="status-icon status-done">✓</span>'
            : st === "current" ? '<span class="status-icon status-current">→</span>'
                : '<span class="status-icon status-needed">○</span>';
        const rowCls = st === "done" ? "row-done" : st === "current" ? "row-current" : "";
        if (code && (st === "done" || st === "current")) {
            creditedRequirementKeys.add(canonicalRequirementCode(code));
        }
        const altCls = isAlt ? " alt-row" : "";
        const codeHtml = code ? `<span class="course-code">${first}</span>` : first;
        tableHtml += `<tr class="${rowCls}${altCls}"><td>${icon}</td><td>${codeHtml}</td><td>${cells[1] || ""}</td><td>${creditDisplay}</td></tr>`;
    });

    tableHtml += `</tbody></table>`;
    return { html: tableHtml, done: doneCnt, current: currentCnt, needed: neededCnt, doneCredits, currentCredits, requiredCredits };
}

function cleanProgramName(value) {
    return String(value || "")
        .replace(/\((?:BA|BS|BFA|BMUS|MINOR|MAJOR)\)/gi, "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
}

function programLabel(program) {
    const title = program?.title || "";
    const award = program?.award || "";
    if (!award || title.toLowerCase().includes(`(${award.toLowerCase()})`)) return title;
    return `${title} (${award})`;
}

function isMinorProgram(program) {
    return /minor/i.test(`${program?.award || ""} ${program?.title || ""} ${program?.url || ""}`);
}

function profileProgramItems(value, fallback, type) {
    const list = Array.isArray(value) ? value : [];
    const items = list
        .map(item => typeof item === "string" ? { title: item } : item)
        .filter(Boolean)
        .map(item => ({
            title: String(item.title || item.name || "").trim(),
            url: String(item.url || "").trim(),
            school: String(item.school || "").trim(),
            award: String(item.award || "").trim(),
            type,
        }))
        .filter(item => item.title || item.url);
    if (items.length || !fallback?.title) return items;
    return [{ ...fallback, type }];
}

function resolveProgramItem(item, availablePrograms) {
    if (item.url) return item;
    const target = cleanProgramName(item.title);
    if (!target) return null;
    const sameType = availablePrograms.filter(program => item.type === "minor" ? isMinorProgram(program) : !isMinorProgram(program));
    const candidates = sameType.length ? sameType : availablePrograms;
    const exact = candidates.find(program => cleanProgramName(program.title) === target || cleanProgramName(programLabel(program)) === target);
    const partial = candidates.find(program => {
        const title = cleanProgramName(program.title);
        return title.includes(target) || target.includes(title);
    });
    const match = exact || partial;
    return match ? { title: match.title, url: match.url, school: match.school || "", award: match.award || "", type: item.type } : item;
}

async function loadPrograms() {
    try {
        const res = await fetch("/api/programs");
        if (!res.ok) return [];
        const programs = await res.json();
        return Array.isArray(programs) ? programs : [];
    } catch {
        return [];
    }
}

function selectedRequirementPrograms(availablePrograms) {
    const legacyMajor = profile.major_url || profile.major
        ? { title: profile.major || "", url: profile.major_url || "", school: profile.school || "", award: "" }
        : null;
    const majorItems = profileProgramItems(profile.majors, legacyMajor, "major");
    const legacyMinorItems = (!Array.isArray(profile.minors) || profile.minors.length === 0) && profile.minor
        ? String(profile.minor).split(",").map(title => ({ title: title.trim(), url: "", school: "", award: "Minor", type: "minor" }))
        : [];
    const minorItems = profileProgramItems(profile.minors, null, "minor").concat(legacyMinorItems);
    const seen = new Set();

    return [...majorItems, ...minorItems]
        .map(item => resolveProgramItem(item, availablePrograms))
        .filter(item => item && item.url)
        .filter(item => {
            if (seen.has(item.url)) return false;
            seen.add(item.url);
            return true;
        });
}

async function render() {
    const root = document.getElementById("page-root");
    const availablePrograms = await loadPrograms();
    const selectedPrograms = selectedRequirementPrograms(availablePrograms);

    if (!selectedPrograms.length) {
        root.innerHTML = `
      <div class="no-major">
        <h2>No programs selected</h2>
        <p>Go to your profile settings and select your majors and minors to see graduation requirements.</p>
        <a href="/profile" class="btn">Go to Settings</a>
      </div>`;
        return;
    }

    let programPayloads;
    try {
        programPayloads = await Promise.all(selectedPrograms.map(async selected => {
            const res = await fetch(`/api/program-requirements?url=${encodeURIComponent(selected.url)}`);
            const prog = await res.json();
            if (!res.ok) throw new Error(prog.error || `Failed to load ${programLabel(selected)}`);
            return { selected, prog };
        }));
    } catch (e) {
        root.innerHTML = `<div class="loading">Error loading requirements: ${e.message}</div>`;
        return;
    }

    const preparedPrograms = programPayloads.map(({ selected, prog }) => {
        const allTables = (prog.tables || []).filter(t => !isSamplePlan(t.label));
        const choiceTables = buildChoiceTables(allTables);
        const tables = allTables.filter(t => !isChoiceTable(t, choiceTables));
        return { selected, prog, choiceTables, tables };
    });
    const lookupCodes = new Set();
    preparedPrograms.forEach(item => {
        collectCourseCreditLookupCodes(item.tables, item.choiceTables).forEach(code => lookupCodes.add(code));
    });
    await loadCourseCatalogCredits(lookupCodes);
    let totalDone = 0, totalCurrent = 0, totalNeeded = 0;
    let totalDoneCredits = 0, totalCurrentCredits = 0, totalRequiredCredits = 0;
    const renderedPrograms = preparedPrograms.map((item, programIndex) => {
        const creditedRequirementKeys = collectSatisfiedRequirementKeys(item.tables, item.choiceTables);
        const assignedElectiveCourseCodes = new Set();
        let programRequiredCredits = 0;
        const sections = item.tables.map((t, tableIndex) => {
            const r = renderTable(t, item.choiceTables, creditedRequirementKeys, assignedElectiveCourseCodes);
            totalDone += r.done;
            totalCurrent += r.current;
            totalNeeded += r.needed;
            totalDoneCredits += r.doneCredits;
            totalCurrentCredits += r.currentCredits;
            programRequiredCredits = Math.max(programRequiredCredits, r.requiredCredits || 0);
            return { label: t.label || "Requirements", id: `sec-${programIndex}-${tableIndex}`, ...r };
        });
        totalRequiredCredits += programRequiredCredits;
        return { ...item, sections, requiredCredits: programRequiredCredits };
    });
    const testCreditsSection = renderStandaloneTestCreditsSection();
    const renderedSections = [
        ...(testCreditsSection ? [testCreditsSection] : []),
        ...renderedPrograms.flatMap(program => {
            const prefix = `${program.selected.type === "minor" ? "Minor" : "Major"} / ${program.prog.title || programLabel(program.selected)}`;
            return program.sections.map(sec => ({ ...sec, label: `${prefix}: ${sec.label}` }));
        }),
    ];
    const totalCourses = totalDone + totalCurrent + totalNeeded;
    const pct = totalCourses ? Math.round((totalDone / totalCourses) * 100) : 0;
    const selectedProgramNames = selectedPrograms.map(program => `${program.type === "minor" ? "Minor: " : ""}${programLabel(program)}`);
    const prog = { school: selectedProgramNames.join(" · ") };
    profile.minor = "";

    let html = `
    <div class="summary-card">
      <div class="summary-info">
        <h2>Graduation Progress</h2>
        <div class="sub">${prog.school || ""}${profile.minor ? " · Minor: " + profile.minor : ""}</div>
        <div class="stat-pills">
          <span class="pill pill-done">✓ ${totalDone} completed</span>
          ${totalCurrent ? `<span class="pill pill-current">→ ${totalCurrent} in progress</span>` : ""}
          <span class="pill pill-needed">○ ${totalNeeded} remaining</span>
          ${totalRequiredCredits ? `<span class="pill pill-done">${formatCredits(totalDoneCredits + totalCurrentCredits)} / ${formatCredits(totalRequiredCredits)} credits</span>` : ""}
          ${testCreditTotal ? `<span class="pill pill-done">${formatCredits(testCreditTotal)} AP/IB/Test credits</span>` : ""}
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

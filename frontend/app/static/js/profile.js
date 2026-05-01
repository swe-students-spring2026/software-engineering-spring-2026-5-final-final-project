// ── Panel switching ────────────────────────────────────────────────────────
function switchPanel(name, navEl) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.side-nav a').forEach(a => a.classList.remove('active'));
    document.getElementById('panel-' + name).classList.add('active');
    navEl.classList.add('active');
    return false;
}

// ── Toast helper ───────────────────────────────────────────────────────────
function showToast(id, msg, type) {
    const el = document.getElementById(id);
    el.className = 'toast ' + type;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

// ── Programs loader for school/major dropdowns ─────────────────────────────
let _allPrograms = [];
const profileDataEl = document.getElementById('profile-data');
const _profileData = profileDataEl ? JSON.parse(profileDataEl.textContent || '{}') : (window.profile || {});
const _savedSchool = _profileData.school || '';
const _savedMajorUrl = _profileData.major_url || '';

async function loadProgramsForSettings() {
    const res = await fetch('/api/programs');
    _allPrograms = await res.json();
    const schools = [...new Set(_allPrograms.map(p => p.school).filter(Boolean))].sort();
    const schoolSel = document.getElementById('s-school');
    schoolSel.innerHTML = '<option value="">Select school</option>' +
        schools.map(s => `<option value="${s}" ${s === _savedSchool ? 'selected' : ''}>${s}</option>`).join('');
    filterMajors();
}

function filterMajors() {
    const school = document.getElementById('s-school').value;
    const majorSel = document.getElementById('s-major');
    const filtered = _allPrograms.filter(p => !school || p.school === school);
    majorSel.innerHTML = '<option value="">Select major</option>' +
        filtered.map(p =>
            `<option value="${p.url}" ${p.url === _savedMajorUrl ? 'selected' : ''}>${p.title}${p.award ? ' (' + p.award + ')' : ''}</option>`
        ).join('');
}

loadProgramsForSettings();

// ── Save settings ──────────────────────────────────────────────────────────
async function saveSettings() {
    const majorSel = document.getElementById('s-major');
    const majorUrl = majorSel.value;
    const majorTitle = majorSel.options[majorSel.selectedIndex]?.text || '';
    const school = document.getElementById('s-school').value;

    const body = {
        name: document.getElementById('s-name').value.trim(),
        school,
        major: majorTitle,
        major_url: majorUrl,
        minor: document.getElementById('s-minor').value.trim(),
        graduation_year: document.getElementById('s-year').value,
        student_id: document.getElementById('s-studentid').value.trim(),
    };

    try {
        const res = await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (res.ok) {
            showToast('settings-toast', '✓ Profile updated successfully.', 'success');
            if (body.name) {
                document.getElementById('sidebar-name').textContent = body.name;
                document.getElementById('avatar-letter').textContent = body.name[0].toUpperCase();
            }
            if (body.major) {
                const badge = document.getElementById('sidebar-major');
                badge.textContent = body.major;
                badge.style.display = '';
            }
            if (body.graduation_year) {
                const el = document.getElementById('sidebar-year');
                if (el) el.textContent = body.graduation_year;
            }
        } else {
            const d = await res.json();
            showToast('settings-toast', d.error || 'Failed to save.', 'error');
        }
    } catch {
        showToast('settings-toast', 'Network error. Please try again.', 'error');
    }
}

// ── Manual course management ───────────────────────────────────────────────
let _courses = _profileData.completed_courses || [];
let _courseSuggestions = [];
let _selectedCourseCode = "";
let _suggestionReqId = 0;

function normalizeCourseText(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
}

function setCoursePickerStatus(message, isError = false) {
    const el = document.getElementById('course-picker-status');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = isError ? '#c00' : '#0a7a2f';
}

function renderCourseSuggestions(items) {
    const container = document.getElementById('course-suggestions');
    if (!container) return;

    if (!items.length) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    container.innerHTML = items.map(course => `
        <button type="button" class="course-suggestion" data-code="${course.code}" data-title="${course.title}">
          <strong>${course.code}</strong>
          <span>${course.title}${course.school ? ` · ${course.school}` : ''}</span>
        </button>
    `).join('');
    container.style.display = 'flex';

    container.querySelectorAll('.course-suggestion').forEach(btn => {
        btn.addEventListener('click', () => {
            const code = btn.dataset.code || '';
            const title = btn.dataset.title || '';
            const input = document.getElementById('add-course-input');
            input.value = code;
            _selectedCourseCode = code;
            setCoursePickerStatus(`Selected ${code}${title ? ` — ${title}` : ''}.`);
            container.style.display = 'none';
            container.innerHTML = '';
        });
    });
}

async function updateCourseSuggestions(query) {
    const term = normalizeCourseText(query);
    const input = document.getElementById('add-course-input');
    const container = document.getElementById('course-suggestions');
    if (!container) return;

    _selectedCourseCode = "";

    if (term.length < 2) {
        renderCourseSuggestions([]);
        setCoursePickerStatus('');
        return;
    }

    const reqId = ++_suggestionReqId;
    try {
        const res = await fetch(`/api/classes?q=${encodeURIComponent(term)}&page=1`);
        const data = await res.json();
        if (reqId !== _suggestionReqId) return;

        const seen = new Set();
        const items = [];
        for (const course of (data.classes || [])) {
            const code = normalizeCourseText(course.code).toUpperCase();
            if (!code || seen.has(code)) continue;
            seen.add(code);
            items.push({ code: course.code, title: course.title || '', school: course.school || '' });
            if (items.length >= 8) break;
        }

        _courseSuggestions = items;
        renderCourseSuggestions(items);
        if (items.length === 0) {
            setCoursePickerStatus('No matching courses found.', true);
        } else {
            setCoursePickerStatus(`Found ${items.length} matching course${items.length === 1 ? '' : 's'}.`);
        }
    } catch {
        if (reqId === _suggestionReqId) {
            renderCourseSuggestions([]);
            setCoursePickerStatus('Could not load course matches.', true);
        }
    }
}

function resolvePickedCourse(rawValue) {
    const normalized = normalizeCourseText(rawValue);
    if (!normalized) return null;

    if (_selectedCourseCode && normalizeCourseText(_selectedCourseCode).toUpperCase() === normalized.toUpperCase()) {
        return _selectedCourseCode;
    }

    const match = _courseSuggestions.find(course => normalizeCourseText(course.code).toUpperCase() === normalized.toUpperCase());
    if (match) return match.code;

    return null;
}

function clearCoursePicker() {
    const input = document.getElementById('add-course-input');
    input.value = '';
    _selectedCourseCode = '';
    _courseSuggestions = [];
    _suggestionReqId += 1;
    renderCourseSuggestions([]);
    setCoursePickerStatus('');
}

function refreshCourseTags(containerId) {
    const container = document.getElementById(containerId);
    if (_courses.length === 0) {
        container.innerHTML = '<div class="empty-state" id="no-courses-msg">No courses added yet.</div>';
    } else {
        container.innerHTML = _courses.map(c =>
            `<div class="course-tag">${c}<button onclick="removeCourse(this,'${c}')">✕</button></div>`
        ).join('');
    }
    document.getElementById('sidebar-course-count').textContent = _courses.length;
}

async function saveCourses() {
    await fetch('/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_courses: _courses }),
    });
}

async function addCourseManually() {
    const input = document.getElementById('add-course-input');
    let selected = resolvePickedCourse(input.value);
    if (!selected) {
        await updateCourseSuggestions(input.value);
        selected = resolvePickedCourse(input.value);
    }
    if (!selected) {
        setCoursePickerStatus('Pick a course from the suggestions first.', true);
        return;
    }
    const val = normalizeCourseText(selected).toUpperCase();
    if (_courses.includes(val)) {
        clearCoursePicker();
        return;
    }
    _courses.push(val);
    clearCoursePicker();
    refreshCourseTags('settings-courses');
    refreshCourseTags('overview-courses');
    refreshCourseTags('transcript-courses');
    saveCourses();
}

document.getElementById('add-course-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addCourseManually();
    }
});

document.getElementById('add-course-input').addEventListener('input', e => {
    updateCourseSuggestions(e.target.value);
});

function removeCourse(btn, course) {
    _courses = _courses.filter(c => c !== course);
    refreshCourseTags('settings-courses');
    refreshCourseTags('overview-courses');
    refreshCourseTags('transcript-courses');
    saveCourses();
}

// ── Transcript upload ──────────────────────────────────────────────────────
function handleDrop(e) {
    e.preventDefault();
    document.getElementById('upload-zone').classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
}

async function handleFileSelect(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showToast('toast-transcript', 'Only PDF files are supported.', 'error');
        return;
    }

    const bar = document.getElementById('progress-bar');
    const fill = document.getElementById('progress-fill');
    bar.style.display = 'block';
    fill.style.width = '30%';

    const formData = new FormData();
    formData.append('transcript', file);

    try {
        fill.style.width = '60%';
        const res = await fetch('/api/transcript', { method: 'POST', body: formData });
        fill.style.width = '100%';

        const data = await res.json();
        if (res.ok) {
            _courses = data.courses || [];
            showToast('toast-transcript', `✓ Parsed ${_courses.length} completed courses from your transcript.`, 'success');

            const parsed = document.getElementById('parsed-results');
            const heading = document.getElementById('parsed-heading');
            const tags = document.getElementById('parsed-courses');
            const currentHeading = document.getElementById('parsed-current-heading');
            const currentTags = document.getElementById('parsed-current-courses');
            const currentCourses = data.current_courses || [];

            heading.textContent = `${_courses.length} completed courses found`;
            tags.innerHTML = _courses.map(c => `<div class="course-tag">${c}</div>`).join('');

            if (currentCourses.length > 0) {
                currentHeading.textContent = `${currentCourses.length} currently enrolled`;
                currentHeading.style.display = '';
                currentTags.innerHTML = currentCourses.map(c => `<div class="course-tag" style="background:#e8f4fd;color:#0369a1">${c}</div>`).join('');

                // Update bottom card
                const bottomCurrent = document.getElementById('transcript-current-courses');
                if (bottomCurrent) {
                    bottomCurrent.style.display = 'flex';
                    bottomCurrent.innerHTML = currentCourses.map(c => `<div class="course-tag" style="background:#e8f4fd;color:#0369a1">${c}</div>`).join('');
                    const h = bottomCurrent.previousElementSibling;
                    if (h && h.tagName === 'H3') h.style.display = '';
                }
            }
            parsed.style.display = 'block';

            refreshCourseTags('settings-courses');
            refreshCourseTags('overview-courses');
            refreshCourseTags('transcript-courses');
        } else {
            showToast('toast-transcript', data.error || 'Upload failed.', 'error');
        }
    } catch {
        showToast('toast-transcript', 'Network error. Please try again.', 'error');
    }

    setTimeout(() => { bar.style.display = 'none'; fill.style.width = '0%'; }, 1200);
}

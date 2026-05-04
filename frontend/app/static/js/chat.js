/* ── AI Chat widget ──────────────────────────────────────────────────────────
   Self-contained. Works on every page.

   Hook for the search page's "Add to schedule" card:
     window.onChatAddCourses = async (items) => { ... return { added, skipped }; }
   If the function is not defined the add-courses block is silently dropped.
──────────────────────────────────────────────────────────────────────────── */

"use strict";

// ── Shared utility (also used by index.js) ──────────────────────────────────
function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
}

// ── State ────────────────────────────────────────────────────────────────────
let chatOpen    = false;
let contextOpen = false;
let chatHistory = [];
const CHAT_HISTORY_LIMIT = 20; // keep last 10 turns (user + model each)

// ── Persistent history (survives page navigation) ─────────────────────────────
const _HISTORY_KEY = "nyu_chat_history";

function _saveHistory() {
    try { localStorage.setItem(_HISTORY_KEY, JSON.stringify(chatHistory)); }
    catch (e) { /* storage full or blocked — silently ignore */ }
}

function _loadHistory() {
    try {
        const raw = localStorage.getItem(_HISTORY_KEY);
        if (raw) chatHistory = JSON.parse(raw);
    } catch (e) {
        chatHistory = [];
    }
}

/** Rebuild the message list from chatHistory after a page load. */
function _restoreMessages() {
    if (!chatHistory.length) return; // nothing to restore; keep the greeting
    const box = document.getElementById("chat-messages");
    box.innerHTML = ""; // remove the default greeting
    for (const entry of chatHistory) {
        const div = document.createElement("div");
        if (entry.role === "user") {
            div.className   = "chat-msg user";
            div.textContent = entry.text;
        } else {
            div.className = "chat-msg ai";
            renderMarkdown(div, entry.text);
        }
        box.appendChild(div);
    }
    box.scrollTop = box.scrollHeight;
}

// ── Drag + side-panel docking ─────────────────────────────────────────────────
// Docking integrates the panel into the flex row of ".main" (search page).
// On pages without ".main" the panel stays floating; dragging still works.
(function () {
    const SNAP_THRESHOLD = 80; // px from left/right edge to trigger dock

    let dragging  = false;
    let didDrag   = false;
    let startX = 0, startY = 0, startLeft = 0, startTop = 0;
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
        const main = document.querySelector(".main");
        if (!main) return; // docking not supported on this page

        const panel = document.getElementById("chat-panel");

        // Move the panel element into .main so it participates in the flex row
        main.appendChild(panel);

        // Clear inline float positioning
        panel.style.cssText = "";

        main.classList.remove("chat-docked-left", "chat-docked-right");
        panel.classList.remove("docked-left", "docked-right", "open");
        panel.classList.add("docked-" + side);
        main.classList.add("chat-docked-" + side);
    }

    function undock() {
        const panel = document.getElementById("chat-panel");
        const main  = document.querySelector(".main");

        panel.classList.remove("docked-left", "docked-right");
        if (main) {
            main.classList.remove("chat-docked-left", "chat-docked-right");
            main.style.removeProperty("--search-width");
            main.style.removeProperty("--cal-width");
        }

        // Move back to body for fixed positioning
        document.body.appendChild(panel);

        // Restore floating position above the bubble (bottom-right)
        panel.style.position = "fixed";
        panel.style.right    = "24px";
        panel.style.bottom   = "80px";
        panel.style.left     = "";
        panel.style.top      = "";
        panel.style.width    = "";
        panel.style.height   = "";
        panel.style.transform = "";

        panel.classList.add("open");
        chatOpen = true;
    }

    function onMouseDown(e) {
        if (e.target.closest("#chat-close-btn")) return;
        const panel = document.getElementById("chat-panel");

        if (isDocked()) {
            const rect = panel.getBoundingClientRect();
            undock();
            panel.style.left   = (e.clientX - rect.width / 2) + "px";
            panel.style.top    = rect.top + "px";
            panel.style.right  = "auto";
            panel.style.bottom = "auto";
            startX    = e.clientX;
            startY    = e.clientY;
            startLeft = e.clientX - rect.width / 2;
            startTop  = rect.top;
        } else {
            const rect = panel.getBoundingClientRect();
            // Neutralise any CSS transform before switching to left/top coords
            panel.style.transform = "none";
            panel.style.left   = rect.left + "px";
            panel.style.top    = rect.top + "px";
            panel.style.right  = "auto";
            panel.style.bottom = "auto";
            startX    = e.clientX;
            startY    = e.clientY;
            startLeft = rect.left;
            startTop  = rect.top;
        }

        dragging = true;
        didDrag  = false;
        panel.classList.add("dragging");
        e.preventDefault();
    }

    function onMouseMove(e) {
        if (!dragging) return;
        didDrag = true;
        const panel  = document.getElementById("chat-panel");
        const rect   = panel.getBoundingClientRect();
        const panelW = rect.width;
        const panelH = rect.height;
        const newLeft = Math.max(-panelW + SNAP_THRESHOLD + 1,
                                  Math.min(startLeft + (e.clientX - startX), window.innerWidth - SNAP_THRESHOLD - 1));
        const newTop  = Math.max(0, Math.min(startTop + (e.clientY - startY), window.innerHeight - panelH));
        panel.style.left = newLeft + "px";
        panel.style.top  = newTop  + "px";

        const canDock = !!document.querySelector(".main");
        if (canDock) {
            if (newLeft <= SNAP_THRESHOLD) {
                showPreview("left");
            } else if (newLeft + panelW >= window.innerWidth - SNAP_THRESHOLD) {
                showPreview("right");
            } else {
                hidePreview();
            }
        }
    }

    function onMouseUp() {
        if (!dragging) return;
        dragging = false;
        hidePreview();
        const panel  = document.getElementById("chat-panel");
        panel.classList.remove("dragging");

        if (!didDrag) return;

        const left   = parseFloat(panel.style.left);
        const panelW = panel.getBoundingClientRect().width;
        const canDock = !!document.querySelector(".main");

        if (canDock && left <= SNAP_THRESHOLD) {
            dock("left");
        } else if (canDock && left + panelW >= window.innerWidth - SNAP_THRESHOLD) {
            dock("right");
        } else {
            panel.style.transform = "none";
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.getElementById("chat-panel-header").addEventListener("mousedown", onMouseDown);
    });
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup",   onMouseUp);
})();

// ── Toggle open / close ──────────────────────────────────────────────────────
function toggleChat() {
    const panel = document.getElementById("chat-panel");
    const main  = document.querySelector(".main");
    const docked = panel.classList.contains("docked-left") || panel.classList.contains("docked-right");

    if (docked) {
        // Closing while docked: remove from layout, move back to body
        panel.classList.remove("docked-left", "docked-right");
        if (main) {
            main.classList.remove("chat-docked-left", "chat-docked-right");
            main.style.removeProperty("--search-width");
            main.style.removeProperty("--cal-width");
        }
        document.body.appendChild(panel);
        panel.style.position  = "fixed";
        panel.style.right     = "24px";
        panel.style.bottom    = "80px";
        panel.style.left      = "";
        panel.style.top       = "";
        panel.style.width     = "";
        panel.style.height    = "";
        panel.style.transform = "";
        chatOpen = false;
        return;
    }

    chatOpen = !chatOpen;
    panel.classList.toggle("open", chatOpen);
    if (chatOpen) document.getElementById("chat-input").focus();
}

// ── Context panel ────────────────────────────────────────────────────────────
function toggleContext() {
    contextOpen = !contextOpen;
    document.getElementById("chat-context-fields").style.display = contextOpen ? "flex" : "none";
    document.getElementById("chat-context-arrow").textContent    = contextOpen ? "▾" : "▸";
}

// ── Typing indicator ─────────────────────────────────────────────────────────
const _THINKING_MSGS = [
    "Searching the course catalog…",
    "Checking prerequisites…",
    "Looking up sections…",
    "Comparing schedules…",
    "Finding the best options…",
    "Reviewing requirements…",
    "Almost there…",
];
let _thinkingInterval = null;

function appendTyping() {
    const box  = document.getElementById("chat-messages");
    const div  = document.createElement("div");
    div.className = "chat-msg ai typing";

    const dots = document.createElement("span");
    dots.className = "typing-dots";
    dots.innerHTML = "<span></span><span></span><span></span>";

    const label = document.createElement("span");
    label.className  = "typing-text";
    label.textContent = _THINKING_MSGS[0];

    div.appendChild(dots);
    div.appendChild(label);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;

    let i = 1;
    _thinkingInterval = setInterval(() => {
        label.textContent = _THINKING_MSGS[i % _THINKING_MSGS.length];
        i++;
    }, 2500);

    return div;
}

function appendMsg(text, role) {
    const box = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className   = `chat-msg ${role}`;
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

// ── Add-courses block ─────────────────────────────────────────────────────────
// The model can emit a fenced ```add-courses``` JSON block when it proposes a
// schedule.  We strip it from the visible reply and, if the page registered a
// window.onChatAddCourses handler (index.js does), show a confirmation card.
const _ADD_COURSES_BLOCK_RE = /```add-courses\s*([\s\S]*?)```/i;

function extractAddCoursesBlock(text) {
    const match = text.match(_ADD_COURSES_BLOCK_RE);
    if (!match) return { cleanText: text, items: [] };
    const cleanText = text.replace(_ADD_COURSES_BLOCK_RE, "").trimEnd();
    let items = [];
    try {
        const parsed = JSON.parse(match[1].trim());
        if (Array.isArray(parsed)) {
            items = parsed
                .map(it => ({
                    code:       String(it?.code       || "").trim(),
                    crn:        String(it?.crn        || "").trim(),
                    title:      String(it?.title      || "").trim(),
                    section:    String(it?.section    || "").trim(),
                    meets_human:String(it?.meets_human|| "").trim(),
                    instructor: String(it?.instructor || "").trim(),
                }))
                .filter(it => it.code && it.crn);
        }
    } catch (e) {
        console.warn("Failed to parse add-courses block:", e);
    }
    return { cleanText, items };
}

function renderAddCoursesCard(items) {
    // Only show the card on pages that registered an add-to-schedule handler
    if (typeof window.onChatAddCourses !== "function") return;

    const box  = document.getElementById("chat-messages");
    const card = document.createElement("div");
    card.className = "chat-msg ai chat-add-card";
    let working = items.slice();

    function paint() {
        if (!working.length) {
            card.innerHTML = `<div class="chat-add-empty">No courses to add.</div>`;
            return;
        }
        card.innerHTML = `
            <div class="chat-add-header">Add these to your calendar?</div>
            <div class="chat-add-list">
                ${working.map((it, i) => `
                    <div class="chat-add-row" data-i="${i}">
                        <div class="chat-add-main">
                            <div class="chat-add-code"><strong>${escapeHtml(it.code)}</strong>${it.title ? ` — ${escapeHtml(it.title)}` : ""}</div>
                            <div class="chat-add-meta">
                                ${it.section     ? `Sec ${escapeHtml(it.section)}`     : ""}
                                ${it.meets_human ? ` · ${escapeHtml(it.meets_human)}`  : ""}
                                ${it.instructor  ? ` · ${escapeHtml(it.instructor)}`   : ""}
                            </div>
                        </div>
                        <button class="chat-add-drop" title="Remove from proposal" data-i="${i}">✕</button>
                    </div>
                `).join("")}
            </div>
            <div class="chat-add-actions">
                <button class="chat-add-confirm">Add ${working.length} to calendar</button>
                <button class="chat-add-cancel">Dismiss</button>
            </div>
        `;
        card.querySelectorAll(".chat-add-drop").forEach(btn => {
            btn.addEventListener("click", () => {
                working.splice(Number(btn.dataset.i), 1);
                paint();
            });
        });
        card.querySelector(".chat-add-cancel").addEventListener("click", () => card.remove());
        card.querySelector(".chat-add-confirm").addEventListener("click", async () => {
            const confirmBtn = card.querySelector(".chat-add-confirm");
            confirmBtn.disabled    = true;
            confirmBtn.textContent = "Adding…";
            const result = await window.onChatAddCourses(working);
            const lines  = [];
            if (result.added)          lines.push(`✓ Added ${result.added} course${result.added === 1 ? "" : "s"}.`);
            if (result.skipped.length) lines.push(`Skipped: ${result.skipped.join("; ")}.`);
            card.innerHTML = `<div class="chat-add-result">${lines.length ? lines.map(escapeHtml).join(" ") : "Nothing was added."}</div>`;
        });
    }

    paint();
    box.appendChild(card);
    box.scrollTop = 999999;
}

// ── Input auto-resize ────────────────────────────────────────────────────────
function autoResizeInput() {
    const el = document.getElementById("chat-input");
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ── History helpers ──────────────────────────────────────────────────────────
function trimHistory() {
    if (chatHistory.length > CHAT_HISTORY_LIMIT) {
        chatHistory = chatHistory.slice(-CHAT_HISTORY_LIMIT);
    }
    _saveHistory();
}

function clearChatHistory() {
    chatHistory = [];
    _saveHistory();
    document.getElementById("chat-messages").innerHTML =
        '<div class="chat-msg ai">Hi! I can help you find courses and plan your schedule. Ask me anything!</div>';
}

// ── Send message ─────────────────────────────────────────────────────────────
async function sendChat() {
    const input = document.getElementById("chat-input");
    const btn   = document.getElementById("chat-send-btn");
    const msg   = input.value.trim();
    if (!msg) return;

    input.value      = "";
    input.style.height = "auto";
    btn.disabled     = true;
    appendMsg(msg, "user");
    const typing = appendTyping();

    const historyForRequest = chatHistory.slice();

    try {
        const major       = document.getElementById("chat-major").value.trim();
        const coursesRaw  = document.getElementById("chat-courses").value.trim();
        const completed_courses = coursesRaw
            ? coursesRaw.split(",").map(s => s.trim()).filter(Boolean)
            : [];

        const res = await fetch("/api/chat", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ message: msg, major, completed_courses, history: historyForRequest }),
        });
        const data     = await res.json();
        const rawReply = data.reply || data.error || "Something went wrong.";
        const { cleanText, items } = data.reply
            ? extractAddCoursesBlock(rawReply)
            : { cleanText: rawReply, items: [] };

        clearInterval(_thinkingInterval);
        typing.classList.remove("typing");
        typing.classList.add("fade-in");
        renderMarkdown(typing, cleanText);
        document.getElementById("chat-messages").scrollTop = 999999;

        if (items.length) renderAddCoursesCard(items);

        if (data.reply) {
            chatHistory.push({ role: "user",  text: msg });
            chatHistory.push({ role: "model", text: cleanText });
            trimHistory(); // also calls _saveHistory()
        }
    } catch {
        clearInterval(_thinkingInterval);
        typing.textContent = "Network error. Please try again.";
        typing.classList.remove("typing");
    } finally {
        btn.disabled = false;
        input.focus();
    }
}

// ── Event listeners + startup ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
    // Restore history from the previous session before wiring up events
    _loadHistory();
    _restoreMessages();

    const input = document.getElementById("chat-input");
    input.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
    });
    input.addEventListener("input", autoResizeInput);
});

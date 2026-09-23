/**
 * Transcript Insight - Client Application Controller
 * Handles authentication, data fetching, matrix rendering,
 * multi-threaded chat, citation inspection, and modals.
 */

// Global state
let currentAppState = null;
let currentConversations = [];
let activeConvId = null;
let currentInspectedTurnId = null;
let drawerTurnId = null;

// Status badge dictionary
const STATUS_CONFIG = {
  answered: { label: "Answered", icon: "fa-circle-check", class: "answered" },
  partial: { label: "Partial", icon: "fa-circle-half-stroke", class: "partial" },
  not_discussed: { label: "Not discussed", icon: "fa-circle-minus", class: "not_discussed" }
};

const DISAGREEMENT_TYPE_CONFIG = {
  contradiction: { label: "Direct contradiction", class: "contradiction", icon: "fa-circle-xmark" },
  emphasis: { label: "Difference in emphasis", class: "emphasis", icon: "fa-circle-exclamation" },
  scope: { label: "Difference in scope", class: "scope", icon: "fa-arrows-split-up-and-left" }
};

// ============================================================================
// Initialization & Authentication
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  checkAuthStatus();
});

async function checkAuthStatus() {
  try {
    const res = await fetch("/api/auth/status");
    const data = await res.json();
    if (data.authenticated) {
      setAuthenticatedUI(true, data.username);
      await loadInitialState();
    } else {
      setAuthenticatedUI(false);
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    setAuthenticatedUI(false);
  }
}

function setAuthenticatedUI(isAuthenticated, username = "admin") {
  const authScreen = document.getElementById("auth-screen");
  const workspace = document.getElementById("app-workspace");
  const navUsername = document.getElementById("nav-username");

  if (isAuthenticated) {
    authScreen.classList.add("hidden");
    workspace.classList.remove("hidden");
    if (navUsername) navUsername.textContent = username;
  } else {
    authScreen.classList.remove("hidden");
    workspace.classList.add("hidden");
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");
  const submitBtn = document.getElementById("btn-login-submit");

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Verifying...</span>`;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value,
        password: passwordInput.value,
      }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Signed in successfully", "success");
      setAuthenticatedUI(true, data.username);
      await loadInitialState();
    } else {
      showToast(data.error || "Login failed", "error");
    }
  } catch (err) {
    showToast("Network error during login", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>Sign In to Workspace</span> <i class="fa-solid fa-arrow-right"></i>`;
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    setAuthenticatedUI(false);
    showToast("Logged out", "info");
  } catch (err) {
    console.error("Logout error:", err);
  }
}

// ============================================================================
// State Loading & Top-Level Setup
// ============================================================================

async function loadInitialState() {
  try {
    const res = await fetch("/api/state");
    if (!res.ok) {
      if (res.status === 401) {
        setAuthenticatedUI(false);
        return;
      }
      throw new Error("Failed to load state");
    }
    const state = await res.json();
    currentAppState = state;

    // Update Header Counts
    document.getElementById("badge-expert-count").textContent = `${state.experts.length} Experts`;
    document.getElementById("badge-question-count").textContent = `${state.guide_questions.length} Questions`;

    // Populate Filters & Selects
    populateCountryFilter(state.countries);
    populateTurnSelect(state.all_turn_ids);

    // Render Subsystems
    renderExpertsHeader(state.experts);
    renderGuideMatrix(state);
    renderThemesAndDisagreements(state.synthesis);
    await loadChatConversations();

  } catch (err) {
    console.error("Error loading application state:", err);
    showToast("Failed to load analysis state", "error");
  }
}

function populateCountryFilter(countries) {
  const filter = document.getElementById("country-filter");
  if (!filter) return;
  filter.innerHTML = `<option value="ALL">All Countries</option>`;
  countries.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    filter.appendChild(opt);
  });
}

function populateTurnSelect(allTurnIds) {
  const select = document.getElementById("citation-turn-select");
  if (!select) return;
  select.innerHTML = `<option value="">-- Choose a Turn ID --</option>`;
  (allTurnIds || []).forEach(id => {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = id;
    select.appendChild(opt);
  });
}

// ============================================================================
// Tab 1: Guide Answers Matrix Rendering
// ============================================================================

function renderExpertsHeader(experts) {
  const container = document.getElementById("experts-header-bar");
  if (!container) return;

  let html = `
    <div class="expert-column-header" style="background: rgba(255,255,255,0.03);">
      <div class="expert-info">
        <span class="expert-name-title" style="color: var(--amber-primary);">Guide Questions</span>
        <span class="expert-role-subtitle">Protocol Matrix</span>
      </div>
    </div>
  `;

  experts.forEach(exp => {
    html += `
      <div class="expert-column-header">
        <div class="expert-country-flag">${exp.country_code || exp.country.substring(0, 2).toUpperCase()}</div>
        <div class="expert-info">
          <span class="expert-name-title">${escapeHtml(exp.expert_name)}</span>
          <span class="expert-role-subtitle">${escapeHtml(exp.expert_role)} (${escapeHtml(exp.country)})</span>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderGuideMatrix(state) {
  const container = document.getElementById("guide-matrix-container");
  if (!container) return;

  const questions = state.guide_questions || [];
  const answerGrid = state.answer_grid || [];
  const countries = state.countries || [];

  if (questions.length === 0) {
    container.innerHTML = `<div class="empty-state">No guide questions found in dataset.</div>`;
    return;
  }

  let html = "";

  questions.forEach(q => {
    html += `
      <div class="question-row-card" data-q-num="${q.number}" data-q-text="${escapeHtml(q.text).toLowerCase()}">
        <div class="question-row-header">
          <span class="q-badge">Q${q.number}</span>
          <h4 class="q-title">${escapeHtml(q.text)}</h4>
        </div>
        <div class="answers-grid-row">
    `;

    countries.forEach(country => {
      const cell = answerGrid.find(c => c.question_number === q.number && c.country === country);
      html += renderAnswerCell(country, cell);
    });

    html += `
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function renderAnswerCell(country, cell) {
  if (!cell) {
    return `
      <div class="answer-cell" data-country="${country}">
        <div class="cell-top-bar">
          <span class="cell-country">${escapeHtml(country)}</span>
          <span class="status-badge not_discussed"><i class="fa-solid fa-circle-minus"></i> No data</span>
        </div>
        <p class="cell-short-answer text-muted">No analysis available for this expert.</p>
      </div>
    `;
  }

  if (cell.generation_failed) {
    return `
      <div class="answer-cell" data-country="${country}">
        <div class="cell-top-bar">
          <span class="cell-country">${escapeHtml(country)}</span>
          <span class="status-badge not_discussed"><i class="fa-solid fa-triangle-exclamation"></i> Flagged</span>
        </div>
        <p class="cell-short-answer text-muted">Generation failed - marked for manual analyst review.</p>
      </div>
    `;
  }

  const statusInfo = STATUS_CONFIG[cell.status] || { label: cell.status, icon: "fa-circle-info", class: "partial" };
  const quotes = cell.quotes || [];
  const quotesCount = quotes.length;

  let quotesHtml = "";
  if (quotesCount > 0) {
    quotesHtml = `
      <div class="quotes-accordion">
        <button class="quotes-toggle-btn" onclick="toggleQuotesAccordion(this)">
          <i class="fa-solid fa-chevron-down"></i>
          <span>${quotesCount} verified quote${quotesCount > 1 ? "s" : ""}</span>
        </button>
        <div class="quotes-list-wrap">
          ${quotes.map(q => `
            <div class="quote-verbatim-card">
              <blockquote>"${escapeHtml(q.text)}"</blockquote>
              <div class="quote-citation-meta">
                <span>— ${escapeHtml(q.country)} @ <strong>${escapeHtml(q.timestamp)}</strong></span>
                <span class="citation-pill" onclick="openCitationDrawer('${escapeHtml(q.turn_id)}')">
                  <i class="fa-solid fa-quote-left"></i> ${escapeHtml(q.turn_id)}
                </span>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  } else {
    quotesHtml = `
      <div class="quotes-accordion">
        <span class="field-hint"><i class="fa-solid fa-info-circle"></i> No quotable evidence found.</span>
      </div>
    `;
  }

  return `
    <div class="answer-cell" data-country="${country}">
      <div class="cell-top-bar">
        <span class="cell-country">${escapeHtml(country)}</span>
        <span class="status-badge ${statusInfo.class}">
          <i class="fa-solid ${statusInfo.icon}"></i> ${statusInfo.label}
        </span>
      </div>
      <p class="cell-short-answer">${escapeHtml(cell.short_answer)}</p>
      ${quotesHtml}
    </div>
  `;
}

function toggleQuotesAccordion(btn) {
  btn.classList.toggle("open");
  const list = btn.nextElementSibling;
  if (list) {
    list.classList.toggle("open");
  }
}

function filterGuideMatrix() {
  const textQuery = (document.getElementById("guide-filter-input")?.value || "").toLowerCase().trim();
  const selectedCountry = document.getElementById("country-filter")?.value || "ALL";

  const questionCards = document.querySelectorAll(".question-row-card");
  questionCards.forEach(card => {
    const qText = card.getAttribute("data-q-text") || "";
    const cardContent = card.innerText.toLowerCase();
    const matchesText = !textQuery || qText.includes(textQuery) || cardContent.includes(textQuery);

    if (matchesText) {
      card.classList.remove("hidden");
    } else {
      card.classList.add("hidden");
    }

    // Filter country columns if specific country chosen
    const cells = card.querySelectorAll(".answer-cell");
    cells.forEach(cell => {
      const country = cell.getAttribute("data-country");
      if (selectedCountry === "ALL" || country === selectedCountry) {
        cell.classList.remove("hidden");
      } else {
        cell.classList.add("hidden");
      }
    });
  });
}

// ============================================================================
// Tab 2: Themes & Disagreements Rendering
// ============================================================================

function renderThemesAndDisagreements(synthesis) {
  const themesContainer = document.getElementById("themes-list");
  const disagreementsContainer = document.getElementById("disagreements-list");
  const themeCountBadge = document.getElementById("theme-count-text");
  const disagreementCountBadge = document.getElementById("disagreement-count-text");

  if (!synthesis) {
    if (themesContainer) themesContainer.innerHTML = `<p class="text-muted">No synthesis available.</p>`;
    if (disagreementsContainer) disagreementsContainer.innerHTML = `<p class="text-muted">No synthesis available.</p>`;
    return;
  }

  const themes = synthesis.themes || [];
  const disagreements = synthesis.disagreements || [];

  if (themeCountBadge) themeCountBadge.textContent = `${themes.length} Themes`;
  if (disagreementCountBadge) disagreementCountBadge.textContent = `${disagreements.length} Disagreements`;

  // Render Themes
  if (themesContainer) {
    if (themes.length === 0) {
      themesContainer.innerHTML = `<p class="text-muted">No cross-expert themes were identified with verifiable evidence.</p>`;
    } else {
      themesContainer.innerHTML = themes.map(th => `
        <div class="theme-card">
          <div class="card-header-line">
            <h4 class="theme-title">${escapeHtml(th.title)}</h4>
            <span class="countries-tag"><i class="fa-solid fa-earth-europe"></i> ${th.countries.join(", ") || "—"}</span>
          </div>
          <p class="card-desc">${escapeHtml(th.description)}</p>
          ${renderSupportingQuotesAccordion(th.supporting_quotes)}
        </div>
      `).join("");
    }
  }

  // Render Disagreements
  if (disagreementsContainer) {
    if (disagreements.length === 0) {
      disagreementsContainer.innerHTML = `<p class="text-muted">No disagreements were identified with verifiable evidence.</p>`;
    } else {
      disagreementsContainer.innerHTML = disagreements.map(dis => {
        const typeInfo = DISAGREEMENT_TYPE_CONFIG[dis.type] || { label: dis.type, class: "emphasis", icon: "fa-bolt" };
        const quotes = dis.quotes_by_country || [];

        return `
          <div class="disagreement-card">
            <div class="card-header-line">
              <h4 class="theme-title">${escapeHtml(dis.title)}</h4>
              <span class="disagreement-type-badge ${typeInfo.class}">
                <i class="fa-solid ${typeInfo.icon}"></i> ${typeInfo.label}
              </span>
            </div>
            ${dis.needs_review ? `
              <div class="review-flag-banner">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>Flagged for manual analyst review (classification ambiguous)</span>
              </div>
            ` : ""}
            <p class="card-desc">${escapeHtml(dis.description)}</p>
            ${renderSupportingQuotesAccordion(quotes)}
          </div>
        `;
      }).join("");
    }
  }
}

function renderSupportingQuotesAccordion(quotes) {
  if (!quotes || quotes.length === 0) return "";
  return `
    <div class="quotes-accordion">
      <button class="quotes-toggle-btn" onclick="toggleQuotesAccordion(this)">
        <i class="fa-solid fa-chevron-down"></i>
        <span>${quotes.length} cited quote${quotes.length > 1 ? "s" : ""}</span>
      </button>
      <div class="quotes-list-wrap">
        ${quotes.map(q => `
          <div class="quote-verbatim-card">
            <blockquote>"${escapeHtml(q.text)}"</blockquote>
            <div class="quote-citation-meta">
              <span>— ${escapeHtml(q.country)} @ <strong>${escapeHtml(q.timestamp)}</strong></span>
              <span class="citation-pill" onclick="openCitationDrawer('${escapeHtml(q.turn_id)}')">
                <i class="fa-solid fa-quote-left"></i> ${escapeHtml(q.turn_id)}
              </span>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

// ============================================================================
// Tab 3: Multi-Threaded Ask Chat
// ============================================================================

async function loadChatConversations() {
  try {
    const res = await fetch("/api/chat/conversations");
    const convs = await res.json();
    currentConversations = convs || [];

    if (currentConversations.length > 0) {
      if (!activeConvId || !currentConversations.find(c => c.id === activeConvId)) {
        activeConvId = currentConversations[0].id;
      }
    }

    renderChatThreadsList();
    renderActiveConversation();
  } catch (err) {
    console.error("Failed to load chat conversations:", err);
  }
}

function renderChatThreadsList() {
  const list = document.getElementById("chat-threads-list");
  if (!list) return;

  list.innerHTML = currentConversations.map(conv => {
    const isActive = conv.id === activeConvId;
    return `
      <button class="thread-item ${isActive ? "active" : ""}" onclick="selectConversation('${conv.id}')">
        <i class="fa-solid ${isActive ? "fa-message" : "fa-comment"}"></i>
        <span>${escapeHtml(conv.title || "New chat")}</span>
      </button>
    `;
  }).join("");
}

function selectConversation(convId) {
  activeConvId = convId;
  renderChatThreadsList();
  renderActiveConversation();
}

async function handleNewChat() {
  try {
    const res = await fetch("/api/chat/conversations", { method: "POST" });
    const newConv = await res.json();
    currentConversations.unshift(newConv);
    activeConvId = newConv.id;
    renderChatThreadsList();
    renderActiveConversation();
  } catch (err) {
    showToast("Failed to create new chat", "error");
  }
}

async function handleDeleteCurrentChat() {
  if (!activeConvId) return;
  if (!confirm("Are you sure you want to delete this chat thread?")) return;

  try {
    const res = await fetch(`/api/chat/conversations/${activeConvId}`, { method: "DELETE" });
    const data = await res.json();
    currentConversations = data.conversations || [];
    activeConvId = currentConversations.length > 0 ? currentConversations[0].id : null;
    renderChatThreadsList();
    renderActiveConversation();
    showToast("Chat thread deleted", "info");
  } catch (err) {
    showToast("Failed to delete chat", "error");
  }
}

function renderActiveConversation() {
  const container = document.getElementById("chat-messages-container");
  const titleEl = document.getElementById("chat-active-title");
  if (!container) return;

  const conv = currentConversations.find(c => c.id === activeConvId);
  if (!conv) {
    container.innerHTML = `<div class="empty-state">Select or start a conversation to begin.</div>`;
    if (titleEl) titleEl.textContent = "Chat";
    return;
  }

  if (titleEl) titleEl.textContent = conv.title || "Conversation";

  if (!conv.messages || conv.messages.length === 0) {
    container.innerHTML = `
      <div class="empty-selection-placeholder" style="padding: 40px 20px;">
        <div class="placeholder-icon"><i class="fa-solid fa-comments"></i></div>
        <h3>Ask any question about the interviews</h3>
        <p>Answers are grounded strictly in the expert call transcripts with verified verbatim citations.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = conv.messages.map(msg => {
    const isUser = msg.role === "user";
    return `
      <div class="chat-message ${isUser ? "user" : "assistant"}">
        <div class="chat-avatar">
          <i class="fa-solid ${isUser ? "fa-user" : "fa-robot"}"></i>
        </div>
        <div class="chat-bubble">
          ${formatChatMessageContent(msg.content)}
        </div>
      </div>
    `;
  }).join("");

  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
}

function formatChatMessageContent(content) {
  if (!content) return "";
  
  // Format citations like [France FR-04 @ 01:20] into clickable pills
  let formatted = escapeHtml(content);

  // Replace [Country TurnID @ Time] pattern with clickable pill
  formatted = formatted.replace(/\[([A-Za-z\s]+)\s+([A-Z]{2}-\d+)\s+@\s+([0-9:]+)\]/g, (match, country, turnId, time) => {
    return `<span class="citation-pill" onclick="openCitationDrawer('${turnId}')"><i class="fa-solid fa-quote-left"></i> ${turnId} (${country} @ ${time})</span>`;
  });

  // Convert newlines to paragraphs
  const paragraphs = formatted.split("\n\n");
  return paragraphs.map(p => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
}

async function handleSendQuestion(e) {
  e.preventDefault();
  const input = document.getElementById("chat-query-input");
  const sendBtn = document.getElementById("btn-chat-send");
  const question = (input?.value || "").trim();

  if (!question) return;

  input.value = "";
  sendBtn.disabled = true;

  // Optimistically append user message to UI
  const container = document.getElementById("chat-messages-container");
  const userMsgHtml = `
    <div class="chat-message user">
      <div class="chat-avatar"><i class="fa-solid fa-user"></i></div>
      <div class="chat-bubble"><p>${escapeHtml(question)}</p></div>
    </div>
    <div id="chat-typing-indicator" class="chat-message assistant">
      <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
      <div class="chat-bubble">
        <p><i class="fa-solid fa-spinner fa-spin text-amber"></i> Searching transcripts and verifying sentences...</p>
      </div>
    </div>
  `;
  container.insertAdjacentHTML("beforeend", userMsgHtml);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch("/api/chat/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conv_id: activeConvId,
        question: question,
      }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      // Update local conversation
      const idx = currentConversations.findIndex(c => c.id === data.conversation.id);
      if (idx !== -1) {
        currentConversations[idx] = data.conversation;
      } else {
        currentConversations.unshift(data.conversation);
      }
      activeConvId = data.conversation.id;
      renderChatThreadsList();
      renderActiveConversation();
    } else {
      showToast(data.error || "Failed to get answer", "error");
      renderActiveConversation();
    }
  } catch (err) {
    showToast("Error communicating with analyst backend", "error");
    renderActiveConversation();
  } finally {
    sendBtn.disabled = false;
  }
}

// ============================================================================
// Tab 4: Citation Inspector
// ============================================================================

async function handleTurnSelectChange(turnId) {
  if (!turnId) return;
  await inspectTurn(turnId);
}

async function inspectTurn(turnId) {
  currentInspectedTurnId = turnId;
  const container = document.getElementById("citation-inspector-body");
  const select = document.getElementById("citation-turn-select");
  if (select) select.value = turnId;

  if (!container) return;

  container.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading context for turn ${escapeHtml(turnId)}...</p>
    </div>
  `;

  try {
    const res = await fetch(`/api/citations/turn/${encodeURIComponent(turnId)}`);
    const data = await res.json();

    if (!res.ok) {
      container.innerHTML = `<div class="empty-state text-rose">${data.error || "Failed to load turn."}</div>`;
      return;
    }

    renderCitationContext(container, data);
  } catch (err) {
    container.innerHTML = `<div class="empty-state text-rose">Error loading turn details.</div>`;
  }
}

function renderCitationContext(container, data) {
  const { target_turn_id, country, expert_name, expert_role, context_turns } = data;

  let html = `
    <div class="expert-column-header" style="margin-bottom: 16px;">
      <div class="expert-country-flag">${data.country_code || "EX"}</div>
      <div class="expert-info">
        <span class="expert-name-title">${escapeHtml(expert_name)} (${escapeHtml(country)})</span>
        <span class="expert-role-subtitle">${escapeHtml(expert_role)} • Call: ${escapeHtml(data.call)}</span>
      </div>
    </div>
    <div class="turn-dialog-stream">
  `;

  context_turns.forEach(turn => {
    const isTarget = turn.id === target_turn_id;
    html += `
      <div class="turn-card ${isTarget ? "highlighted-turn" : ""}">
        <div class="turn-meta-col">
          <span class="turn-id-tag">${escapeHtml(turn.id)}</span>
          <span class="turn-timestamp"><i class="fa-regular fa-clock"></i> ${escapeHtml(turn.timestamp)}</span>
          ${isTarget ? `<span class="badge text-amber" style="font-size:10px; font-weight:700;">★ CITED</span>` : ""}
        </div>
        <div class="turn-body-col">
          <div class="speaker-label">${escapeHtml(turn.speaker)}</div>
          <div class="turn-text">${escapeHtml(turn.text)}</div>
        </div>
      </div>
    `;
  });

  html += `</div>`;
  container.innerHTML = html;
}

// ============================================================================
// Slide-Over Citation Drawer
// ============================================================================

async function openCitationDrawer(turnId) {
  if (!turnId) return;
  drawerTurnId = turnId;

  const drawer = document.getElementById("citation-drawer");
  const titleEl = document.getElementById("drawer-turn-id");
  const metaBar = document.getElementById("drawer-meta-bar");
  const content = document.getElementById("drawer-content");

  titleEl.textContent = `Turn ${turnId}`;
  metaBar.innerHTML = `<span>Loading context metadata...</span>`;
  content.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Fetching conversational context...</p>
    </div>
  `;

  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");

  try {
    const res = await fetch(`/api/citations/turn/${encodeURIComponent(turnId)}`);
    const data = await res.json();

    if (!res.ok) {
      content.innerHTML = `<p class="text-rose">${data.error || "Turn not found."}</p>`;
      return;
    }

    metaBar.innerHTML = `
      <span><strong>${escapeHtml(data.expert_name)}</strong></span>
      <span>•</span>
      <span>${escapeHtml(data.expert_role)}</span>
      <span>•</span>
      <span class="text-amber">${escapeHtml(data.country)}</span>
    `;

    content.innerHTML = `
      <div class="turn-dialog-stream">
        ${data.context_turns.map(turn => {
          const isTarget = turn.id === turnId;
          return `
            <div class="turn-card ${isTarget ? "highlighted-turn" : ""}">
              <div class="turn-meta-col">
                <span class="turn-id-tag">${escapeHtml(turn.id)}</span>
                <span class="turn-timestamp">${escapeHtml(turn.timestamp)}</span>
              </div>
              <div class="turn-body-col">
                <div class="speaker-label">${escapeHtml(turn.speaker)}</div>
                <div class="turn-text">${escapeHtml(turn.text)}</div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<p class="text-rose">Failed to load turn context.</p>`;
  }
}

function closeCitationDrawer() {
  const drawer = document.getElementById("citation-drawer");
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

function jumpToFullInspectorFromDrawer() {
  const turnId = drawerTurnId;
  closeCitationDrawer();
  if (turnId) {
    switchTab("tab-citation");
    inspectTurn(turnId);
  }
}

// ============================================================================
// Pipeline Operations: Regenerate, Clear Cache, Uploads
// ============================================================================

async function handleRegenerate() {
  if (!confirm("Re-run analysis pipeline? This will call the local LLM and may take a couple minutes.")) return;

  const btn = document.getElementById("btn-regenerate");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Running...</span>`;
  showToast("Pipeline re-run initiated...", "info");

  try {
    const formData = new FormData();
    formData.append("force_regenerate", "true");

    const res = await fetch("/api/pipeline/run", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Pipeline completed successfully!", "success");
      await loadInitialState();
    } else {
      showToast(data.message || data.error || "Regeneration failed", "error");
    }
  } catch (err) {
    showToast("Error executing pipeline", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> <span>Regenerate</span>`;
  }
}

async function handleClearCache() {
  if (!confirm("Clear cached analysis? You will need to regenerate to view results again.")) return;

  try {
    const res = await fetch("/api/cache/clear", { method: "POST" });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Cache cleared", "info");
      await loadInitialState();
    } else {
      showToast("Failed to clear cache", "error");
    }
  } catch (err) {
    showToast("Error clearing cache", "error");
  }
}

// Modal Handlers
function openUploadModal() {
  document.getElementById("upload-modal").classList.remove("hidden");
}

function closeUploadModal() {
  document.getElementById("upload-modal").classList.add("hidden");
}

function handleModalBackdropClick(e) {
  if (e.target.id === "upload-modal") {
    closeUploadModal();
  }
}

async function handleUploadSubmit(e) {
  e.preventDefault();
  const guideInput = document.getElementById("guide-file-input");
  const transcriptInput = document.getElementById("transcript-files-input");
  const forceRegen = document.getElementById("check-force-regenerate").checked;
  const submitBtn = document.getElementById("btn-upload-submit");

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Processing...</span>`;

  try {
    const formData = new FormData();
    if (guideInput.files.length > 0) {
      formData.append("guide_file", guideInput.files[0]);
    }
    if (transcriptInput.files.length > 0) {
      for (let i = 0; i < transcriptInput.files.length; i++) {
        formData.append("transcript_files", transcriptInput.files[i]);
      }
    }
    formData.append("force_regenerate", forceRegen ? "true" : "false");

    const res = await fetch("/api/pipeline/run", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Custom dataset loaded and analyzed!", "success");
      closeUploadModal();
      await loadInitialState();
    } else {
      showToast(data.message || data.error || "Pipeline run failed", "error");
    }
  } catch (err) {
    showToast("Error running pipeline with custom inputs", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<i class="fa-solid fa-play"></i> <span>Run Pipeline</span>`;
  }
}

// ============================================================================
// Tab Switcher & Toast Utilities
// ============================================================================

function switchTab(tabId) {
  // Update buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Update views
  document.querySelectorAll(".tab-view").forEach(view => {
    if (view.id === tabId) {
      view.classList.add("active");
    } else {
      view.classList.remove("active");
    }
  });
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;

  let icon = "fa-circle-info";
  if (type === "success") icon = "fa-circle-check text-emerald";
  if (type === "error") icon = "fa-triangle-exclamation text-rose";

  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (typeof str !== "string") return str == null ? "" : String(str);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

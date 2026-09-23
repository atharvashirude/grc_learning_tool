// GRC Simulation Terminal Client Logic

let currentSessionId = null;
let controlsMap = {};

document.addEventListener("DOMContentLoaded", () => {
  initElements();
  loadControls();
  setupEventListeners();
});

let elements = {};

function initElements() {
  elements = {
    controlSelect: document.getElementById("control-select"),
    btnStartSession: document.getElementById("btn-start-session"),
    chatMessages: document.getElementById("chat-messages"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    btnSend: document.getElementById("btn-send"),
    btnAskHint: document.getElementById("btn-ask-hint"),
    btnSubmitEval: document.getElementById("btn-submit-eval"),
    terminalControlTitle: document.getElementById("terminal-control-title"),
    terminalPhaseBadge: document.getElementById("terminal-phase-badge"),
    sessionBadge: document.getElementById("session-badge"),
    scorecardStatement: document.getElementById("scorecard-statement"),
    findingSeverity: document.getElementById("finding-severity"),
    findingTitle: document.getElementById("finding-title"),
    findingStatement: document.getElementById("finding-statement"),
    findingRemediation: document.getElementById("finding-remediation"),
    findingRemediationText: document.getElementById("finding-remediation-text"),
    scenarioButtons: document.querySelectorAll(".btn-scenario"),
  };
}

async function loadControls() {
  try {
    const res = await fetch("/api/v1/controls");
    if (!res.ok) return;
    const controls = await res.json();
    elements.controlSelect.innerHTML = "";
    controls.forEach((c) => {
      controlsMap[c.code] = c;
      const opt = document.createElement("option");
      opt.value = c.code;
      opt.textContent = `${c.code} - ${c.title}`;
      elements.controlSelect.appendChild(opt);
    });
    updateScorecardPreview(elements.controlSelect.value);
  } catch (err) {
    console.error("Failed to load controls:", err);
  }
}

function updateScorecardPreview(code) {
  const c = controlsMap[code];
  if (c) {
    elements.scorecardStatement.innerHTML = `
      <strong>${c.code}: ${c.title}</strong><br>
      <span style="font-size:0.75rem; color: #00D2FF;">${c.category}</span>
      <p style="margin-top:0.4rem; font-size:0.8rem;">${c.statement}</p>
    `;
  }
}

function setupEventListeners() {
  elements.controlSelect.addEventListener("change", (e) => {
    updateScorecardPreview(e.target.value);
  });

  elements.btnStartSession.addEventListener("click", startSession);

  elements.chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = elements.chatInput.value.trim();
    if (!text || !currentSessionId) return;
    sendTurn(text);
  });

  elements.btnAskHint.addEventListener("click", () => {
    if (!currentSessionId) return;
    sendTurn("I need help or a Socratic hint on what evidence is expected for this control.");
  });

  elements.btnSubmitEval.addEventListener("click", () => {
    if (!currentSessionId) return;
    sendTurn("All controls and evidence configured in the sandbox. Please evaluate and conclude the audit.");
  });

  elements.scenarioButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      elements.scenarioButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const scenario = btn.dataset.scenario;
      await switchScenario(scenario);
    });
  });
}

async function switchScenario(scenario) {
  try {
    const res = await fetch("/api/v1/sandbox/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    if (res.ok) {
      console.log(`Switched to scenario: ${scenario}`);
    }
  } catch (err) {
    console.error("Failed to switch scenario:", err);
  }
}

async function startSession() {
  const controlCode = elements.controlSelect.value;
  elements.btnStartSession.disabled = true;
  elements.btnStartSession.textContent = "Booting Agent Graph...";

  try {
    const res = await fetch("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ control_code: controlCode }),
    });

    if (!res.ok) throw new Error("Session boot failed");
    const data = await res.json();
    currentSessionId = data.session_id;

    elements.terminalControlTitle.textContent = `Audit: ${data.control_code}`;
    elements.terminalPhaseBadge.textContent = `PHASE: ${data.phase}`;
    elements.sessionBadge.textContent = `Session: ${currentSessionId}`;
    elements.sessionBadge.classList.add("badge-active");

    // Enable inputs
    elements.chatInput.disabled = false;
    elements.btnSend.disabled = false;
    elements.chatInput.focus();

    // Clear messages and render opening
    elements.chatMessages.innerHTML = "";
    renderMessages(data.messages);
    updateScorecardFinding(data.finding);
  } catch (err) {
    console.error(err);
    alert("Failed to initialize session. Check server console.");
  } finally {
    elements.btnStartSession.disabled = false;
    elements.btnStartSession.textContent = "Re-Initialize Session";
  }
}

async function sendTurn(userMessage) {
  if (!currentSessionId) return;

  // Optimistically append auditee message
  appendMessage("auditee", userMessage);
  elements.chatInput.value = "";
  elements.chatInput.disabled = true;
  elements.btnSend.disabled = true;

  try {
    const res = await fetch(`/api/v1/sessions/${currentSessionId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: userMessage }),
    });

    if (!res.ok) throw new Error("Turn execution failed");
    const data = await res.json();

    elements.terminalPhaseBadge.textContent = `PHASE: ${data.phase}`;

    // Render latest agent response
    const lastMsg = data.messages[data.messages.length - 1];
    if (lastMsg && lastMsg.role !== "auditee") {
      appendMessage(lastMsg.role, lastMsg.content);
    }

    updateScorecardFinding(data.finding);

    if (data.status === "CONCLUDED") {
      elements.terminalPhaseBadge.textContent = "STATUS: CONCLUDED";
      elements.terminalPhaseBadge.style.color = "#00F5A0";
      elements.btnSubmitEval.disabled = true;
    }
  } catch (err) {
    console.error(err);
    appendMessage("system", "Network or agent execution error.");
  } finally {
    elements.chatInput.disabled = false;
    elements.btnSend.disabled = false;
    elements.chatInput.focus();
  }
}

function renderMessages(messages) {
  messages.forEach((m) => appendMessage(m.role, m.content));
}

function appendMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${role}`;

  const roleTag = document.createElement("span");
  roleTag.className = "role-tag";
  roleTag.textContent = role === "auditor" ? "Lead Auditor" : role === "coach" ? "GRC Coach (Mentor)" : "Auditee";

  const textNode = document.createElement("div");
  textNode.style.whiteSpace = "pre-wrap";
  textNode.textContent = content;

  bubble.appendChild(roleTag);
  bubble.appendChild(textNode);
  elements.chatMessages.appendChild(bubble);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function updateScorecardFinding(finding) {
  if (!finding) return;

  elements.findingSeverity.className = "finding-severity";
  let sevClass = "severity-none";
  let sevText = finding.severity.toUpperCase();

  if (finding.severity.includes("conformant")) {
    sevClass = "severity-conformant";
  } else if (finding.severity.includes("major")) {
    sevClass = "severity-major";
  } else if (finding.severity.includes("minor")) {
    sevClass = "severity-minor";
  } else if (finding.severity.includes("opportunity")) {
    sevClass = "severity-ofi";
  }

  elements.findingSeverity.classList.add(sevClass);
  elements.findingSeverity.textContent = sevText;
  elements.findingTitle.textContent = finding.title;
  elements.findingStatement.textContent = finding.statement;

  if (finding.remediation_guidance) {
    elements.findingRemediation.style.display = "block";
    elements.findingRemediationText.textContent = finding.remediation_guidance;
  } else {
    elements.findingRemediation.style.display = "none";
  }
}

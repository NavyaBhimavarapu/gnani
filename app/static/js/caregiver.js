/**
 * VoiceDose - Caregiver Dashboard Logic
 * Handles:
 * - Live polling of today's doses and voice activity logs
 * - Adherence metric calculations
 * - Manual caregiver dose overrides (Mark Taken, Mark Missed, Snooze)
 * - 1-Click Demo Reset functionality for screen recording
 */

// DOM Elements
const cgPatientName = document.getElementById("cgPatientName");
const statTotal = document.getElementById("statTotal");
const statTaken = document.getElementById("statTaken");
const statPending = document.getElementById("statPending");
const statSnoozed = document.getElementById("statSnoozed");
const dosesTimelineList = document.getElementById("dosesTimelineList");
const logsTableBody = document.getElementById("logsTableBody");
const btnRefreshNow = document.getElementById("btnRefreshNow");
const btnResetDemo = document.getElementById("btnResetDemo");

let pollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  loadCaregiverData();
  setupEventListeners();

  // Auto-refresh every 4 seconds so voice interactions from the elder view appear live
  pollInterval = setInterval(loadCaregiverData, 4000);
});

function setupEventListeners() {
  btnRefreshNow.addEventListener("click", () => {
    btnRefreshNow.style.transform = "rotate(180deg)";
    setTimeout(() => (btnRefreshNow.style.transform = "none"), 300);
    loadCaregiverData();
  });

  btnResetDemo.addEventListener("click", async () => {
    if (!confirm("Reset all doses to initial pending state for demo recording?")) {
      return;
    }
    try {
      const res = await fetch("/api/reset-demo", { method: "POST" });
      if (res.ok) {
        await loadCaregiverData();
        alert("Demo schedule reset! All doses are now ready for testing.");
      }
    } catch (err) {
      console.error("Failed to reset demo data:", err);
    }
  });
}

/**
 * Fetch and render all caregiver dashboard data
 */
async function loadCaregiverData() {
  try {
    const res = await fetch("/api/caregiver/summary");
    if (!res.ok) throw new Error("Failed to fetch caregiver summary");

    const data = await res.json();
    renderStats(data.stats);
    renderDosesTimeline(data.doses);
    renderLogs(data.recent_logs);
  } catch (err) {
    console.error("Caregiver data load error:", err);
  }
}

/**
 * Update summary KPI stats
 */
function renderStats(stats) {
  if (!stats) return;
  statTotal.textContent = stats.total;
  statTaken.textContent = stats.taken;
  statPending.textContent = stats.pending;
  statSnoozed.textContent = stats.snoozed + stats.missed;
}

/**
 * Render today's doses cards
 */
function renderDosesTimeline(doses) {
  if (!doses || doses.length === 0) {
    dosesTimelineList.innerHTML = `<div style="padding: 2rem; text-align: center; color: #64748b;">No doses scheduled for today.</div>`;
    return;
  }

  dosesTimelineList.innerHTML = "";

  doses.forEach((dose) => {
    const card = document.createElement("div");
    card.className = "dose-row-card";

    // Status styling
    let statusClass = `status-${dose.status}`;
    let statusLabel = "● Pending";
    if (dose.status === "taken") statusLabel = "✅ Taken";
    if (dose.status === "snoozed") statusLabel = "⏰ Snoozed";
    if (dose.status === "missed") statusLabel = "⚠️ Missed";

    // Voice verification snippet
    let voiceTranscriptHtml = "";
    if (dose.voice_transcript) {
      voiceTranscriptHtml = `
        <div class="dose-voice-transcript-tag">
          <span>🎙️ Voice response:</span>
          <strong>"${dose.voice_transcript}"</strong>
          <span style="color: #64748b;">(${dose.logged_at || "Just now"})</span>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="dose-time-column">
        <div class="dose-slot-label">${dose.slot_name}</div>
        <div class="dose-time-display">${dose.scheduled_time}</div>
      </div>

      <div class="dose-med-column">
        <div class="dose-med-name">
          ${dose.medicine_name} <span class="dose-med-dosage">${dose.dosage}</span>
        </div>
        <div class="dose-instructions-sub">
          <strong>Instructions:</strong> ${dose.instructions || "Take with water"}
        </div>
        ${voiceTranscriptHtml}
      </div>

      <div class="dose-actions-column">
        <span class="status-badge ${statusClass}">${statusLabel}</span>

        ${
          dose.status !== "taken"
            ? `
          <button class="btn-action-sm btn-take" onclick="overrideDoseStatus(${dose.id}, 'taken')">
            Mark Taken
          </button>
          <button class="btn-action-sm" onclick="overrideDoseStatus(${dose.id}, 'snoozed')">
            Snooze
          </button>
          <button class="btn-action-sm" style="color: #dc2626;" onclick="overrideDoseStatus(${dose.id}, 'missed')">
            Missed
          </button>
        `
            : `
          <button class="btn-action-sm" onclick="overrideDoseStatus(${dose.id}, 'pending')">
            Reopen
          </button>
        `
        }
      </div>
    `;

    dosesTimelineList.appendChild(card);
  });
}

/**
 * Render recent voice activity log table
 */
function renderLogs(logs) {
  if (!logs || logs.length === 0) {
    logsTableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: #94a3b8; padding: 1.5rem;">
          No voice interactions recorded yet today.
        </td>
      </tr>
    `;
    return;
  }

  logsTableBody.innerHTML = "";

  logs.forEach((log) => {
    const tr = document.createElement("tr");

    let langName = "Telugu";
    if (log.language_code === "hi-IN") langName = "Hindi";
    if (log.language_code === "en-IN") langName = "English";

    let intentBadge = `<span class="badge-tag">${log.matched_intent || "unknown"}</span>`;
    if (log.matched_intent === "taken") {
      intentBadge = `<span class="status-badge status-taken" style="font-size:0.75rem;">Taken</span>`;
    } else if (log.matched_intent === "snooze") {
      intentBadge = `<span class="status-badge status-snoozed" style="font-size:0.75rem;">Snooze</span>`;
    } else if (log.matched_intent === "not_yet") {
      intentBadge = `<span class="status-badge status-pending" style="font-size:0.75rem;">Not Yet</span>`;
    }

    tr.innerHTML = `
      <td style="font-weight: 600; white-space: nowrap;">${log.timestamp}</td>
      <td style="font-weight: 700;">${log.medicine_name || "Dose"} (${log.slot_name || "Daily"})</td>
      <td><span class="badge-tag">${langName}</span></td>
      <td style="font-weight: 600; color: #0f172a;">"${log.transcript || "-"}"</td>
      <td>${intentBadge}</td>
      <td style="font-size: 0.85rem; color: #475569; max-width: 250px;">${log.confirmation_spoken || "-"}</td>
    `;

    logsTableBody.appendChild(tr);
  });
}

/**
 * Caregiver manual status override
 */
window.overrideDoseStatus = async function (doseId, status) {
  try {
    const res = await fetch("/api/caregiver/update-dose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dose_id: doseId,
        status: status,
      }),
    });
    if (res.ok) {
      loadCaregiverData();
    }
  } catch (err) {
    console.error("Failed to update dose status:", err);
  }
};

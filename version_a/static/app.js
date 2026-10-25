// State Management
let allJobs = [];
let selectedJobId = null;
let requiredSkillsList = [];
let preferredSkillsList = [];

// Time formatting helper using standard IANA timezone without manual offsets
function formatToIST(isoOrUtcString) {
  if (!isoOrUtcString) return "N/A";
  let s = String(isoOrUtcString).trim();
  if (!s.endsWith("Z") && !s.includes("+")) {
    s = s.replace(" ", "T") + "Z";
  }
  const date = new Date(s);
  if (isNaN(date.getTime())) return isoOrUtcString;

  return new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  }).format(date) + " IST";
}

// DOM Elements
const jobsListContainer = document.getElementById("jobs-list-container");
const jobDetailContainer = document.getElementById("job-detail-container");
const jobsSearchInput = document.getElementById("jobs-search-input");
const jobsCountBadge = document.getElementById("jobs-count-badge");

const metricTotalJobs = document.getElementById("metric-total-jobs");
const metricSyncedJobs = document.getElementById("metric-synced-jobs");
const metricTotalCandidates = document.getElementById("metric-total-candidates");
const metricTopScore = document.getElementById("metric-top-score");

const modalCreateJob = document.getElementById("modal-create-job");
const createJobForm = document.getElementById("create-job-form");
const btnOpenCreateJob = document.getElementById("btn-open-create-job");
const btnCloseModal = document.getElementById("btn-close-modal");
const btnCancelModal = document.getElementById("btn-cancel-modal");
const btnRefreshAll = document.getElementById("btn-refresh-all");

const requiredInput = document.getElementById("required_skills_input");
const preferredInput = document.getElementById("preferred_skills_input");
const requiredTagsContainer = document.getElementById("required-tags");
const preferredTagsContainer = document.getElementById("preferred-tags");
const btnAddRequiredSkill = document.getElementById("btn-add-required-skill");
const btnAddPreferredSkill = document.getElementById("btn-add-preferred-skill");

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadJobs();

  // Background refresh every 6 seconds to update candidates if Version B evaluated new resumes
  setInterval(() => {
    if (selectedJobId) {
      loadCandidatesForJob(selectedJobId, false);
    }
  }, 6000);
});

function setupEventListeners() {
  btnOpenCreateJob.addEventListener("click", openJobModal);
  btnCloseModal.addEventListener("click", closeJobModal);
  btnCancelModal.addEventListener("click", closeJobModal);
  
  btnRefreshAll.addEventListener("click", async () => {
    await loadJobs();
    if (selectedJobId) {
      await loadCandidatesForJob(selectedJobId, false);
    }
    showToast("Dashboard refreshed", "info");
  });

  jobsSearchInput.addEventListener("input", (e) => {
    renderJobsList(e.target.value.trim().toLowerCase());
  });

  createJobForm.addEventListener("submit", handleCreateJob);

  // Skill tags input handling with Add buttons
  setupTagInput(requiredInput, requiredSkillsList, requiredTagsContainer, btnAddRequiredSkill);
  setupTagInput(preferredInput, preferredSkillsList, preferredTagsContainer, btnAddPreferredSkill);
}

function addSkillTag(inputElem, list, container) {
  const raw = inputElem.value;
  if (!raw || !raw.trim()) return;
  const parts = raw.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
  parts.forEach(val => {
    if (!list.includes(val)) {
      list.push(val);
    }
  });
  renderTags(list, container);
  inputElem.value = "";
}

function setupTagInput(inputElem, list, container, addBtn) {
  inputElem.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkillTag(inputElem, list, container);
    }
  });

  inputElem.addEventListener("blur", () => {
    addSkillTag(inputElem, list, container);
  });

  if (addBtn) {
    addBtn.addEventListener("click", () => {
      addSkillTag(inputElem, list, container);
      inputElem.focus();
    });
  }
}

function renderTags(list, container) {
  container.innerHTML = "";
  list.forEach((skill, idx) => {
    const badge = document.createElement("span");
    badge.className = "tag-badge";
    badge.innerHTML = `
      <span>${skill}</span>
      <span class="remove-tag" data-idx="${idx}">&times;</span>
    `;
    badge.querySelector(".remove-tag").addEventListener("click", (e) => {
      e.stopPropagation();
      list.splice(idx, 1);
      renderTags(list, container);
    });
    container.appendChild(badge);
  });
}

async function loadJobs() {
  try {
    const res = await fetch("/jobs");
    if (!res.ok) throw new Error("Failed to load jobs");
    allJobs = await res.json();
    
    updateMetricsSummary();
    renderJobsList(jobsSearchInput.value.trim().toLowerCase());

    if (allJobs.length > 0) {
      if (!selectedJobId || !allJobs.some(j => j.job_id === selectedJobId)) {
        selectJob(allJobs[0].job_id);
      }
    } else {
      selectedJobId = null;
      renderEmptyDetail();
    }
  } catch (err) {
    console.error("Error loading jobs:", err);
    showToast("Could not load jobs from database", "error");
  }
}

function updateMetricsSummary() {
  const total = allJobs.length;
  metricTotalJobs.textContent = total;
  if (jobsCountBadge) jobsCountBadge.textContent = total;
  
  const syncedCount = allJobs.filter(j => j.sync_status === "synced").length;
  metricSyncedJobs.textContent = syncedCount;
}

function renderJobsList(query = "") {
  jobsListContainer.innerHTML = "";
  
  const q = (query || "").trim().toLowerCase();
  const filtered = allJobs.filter(j => {
    if (!q) return true;
    const titleMatch = (j.job_title || "").toLowerCase().includes(q);
    const idMatch = (j.job_id || "").toLowerCase().includes(q);
    const reqSkillsMatch = Array.isArray(j.required_skills) && j.required_skills.some(s => (s || "").toLowerCase().includes(q));
    const prefSkillsMatch = Array.isArray(j.preferred_skills) && j.preferred_skills.some(s => (s || "").toLowerCase().includes(q));
    return titleMatch || idMatch || reqSkillsMatch || prefSkillsMatch;
  });

  if (filtered.length === 0) {
    jobsListContainer.innerHTML = `
      <div class="empty-state">
        <p>${q ? 'No matching jobs found.' : 'No job postings yet.<br>Click <strong>+ Post Job</strong> to create one.'}</p>
      </div>
    `;
    return;
  }

  filtered.forEach(job => {
    const item = document.createElement("div");
    item.className = `job-item ${job.job_id === selectedJobId ? "selected" : ""}`;
    item.dataset.id = job.job_id;

    const skillsHtml = (job.required_skills || []).slice(0, 3).map(s => `<span class="skill-pill">${s}</span>`).join("");
    const moreSkills = (job.required_skills || []).length > 3 ? `<span class="skill-pill">+${job.required_skills.length - 3}</span>` : "";

    item.innerHTML = `
      <div class="job-item-header">
        <span class="job-item-id">${job.job_id}</span>
        <span style="font-size: 0.72rem; color: var(--text-muted);">${formatToIST(job.created_at)}</span>
      </div>
      <div class="job-item-title">${job.job_title}</div>
      <div class="job-item-meta">
        <span>Min Exp: ${job.min_experience} yrs</span>
      </div>
      <div class="job-item-skills">
        ${skillsHtml} ${moreSkills}
      </div>
    `;

    item.addEventListener("click", () => selectJob(job.job_id));
    jobsListContainer.appendChild(item);
  });
}

function renderEmptyDetail() {
  metricTotalCandidates.textContent = "0";
  metricTopScore.textContent = "0%";
  jobDetailContainer.className = "job-detail-empty";
  jobDetailContainer.innerHTML = `
    <div class="placeholder-graphic">
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>
      <h3>Select a Job Posting</h3>
      <p>Choose an active job from the left panel to inspect specifications and view ranked candidates calculated by the Candidate Matching Portal.</p>
    </div>
  `;
}

async function selectJob(jobId) {
  selectedJobId = jobId;
  
  document.querySelectorAll(".job-item").forEach(el => {
    el.classList.toggle("selected", el.dataset.id === jobId);
  });

  const job = allJobs.find(j => j.job_id === jobId);
  if (!job) return;

  renderJobDetailsSkeleton(job);
  await loadCandidatesForJob(jobId, false);
}

function renderJobDetailsSkeleton(job) {
  jobDetailContainer.className = "job-detail-content";

  const reqHtml = job.required_skills && job.required_skills.length > 0
    ? job.required_skills.map(s => `<span class="tag-matched">${s}</span>`).join("")
    : '<span style="color: var(--text-muted); font-size: 0.82rem;">None specified</span>';

  const prefHtml = job.preferred_skills && job.preferred_skills.length > 0
    ? job.preferred_skills.map(s => `<span class="skill-pill">${s}</span>`).join("")
    : '<span style="color: var(--text-muted); font-size: 0.82rem;">None specified</span>';

  jobDetailContainer.innerHTML = `
    <div class="job-spec-header">
      <div class="job-spec-top">
        <div>
          <span class="job-item-id">${job.job_id}</span>
          <h2 class="job-spec-title">${job.job_title}</h2>
        </div>
        <div class="job-spec-actions">
          ${job.sync_status !== "synced" ? `
            <button class="btn btn-secondary btn-sm" onclick="retrySyncJob('${job.job_id}')" title="Synchronize with Candidate Matching Portal">
              Sync to Matching Portal
            </button>
          ` : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteJob('${job.job_id}')" title="Delete job">
            Delete
          </button>
        </div>
      </div>

      <p class="job-spec-description">${job.job_description}</p>

      <div class="job-spec-grid">
        <div class="spec-item">
          <label>Min Experience</label>
          <span>${job.min_experience} Years</span>
        </div>
        <div class="spec-item">
          <label>Education</label>
          <span>${job.education_requirement}</span>
        </div>
        <div class="spec-item">
          <label>Posting Date (IST)</label>
          <span>${formatToIST(job.created_at)}</span>
        </div>
      </div>

      <div class="skills-breakdown">
        <div class="skills-group">
          <div class="skills-group-label">Required Skills:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            ${reqHtml}
          </div>
        </div>
        <div class="skills-group" style="margin-top: 10px;">
          <div class="skills-group-label">Preferred Skills:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            ${prefHtml}
          </div>
        </div>
      </div>
    </div>

    <!-- Candidate Leaderboard Container -->
    <div id="candidates-section">
      <div class="candidates-board-header">
        <h3 class="candidates-board-title">
          Ranked Candidates
          <span class="badge-count" id="candidate-count-badge">0</span>
        </h3>
        <button class="btn-refresh-rankings" id="btn-refresh-rankings" onclick="handleRefreshRankings('${job.job_id}')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          <span>Refresh Rankings</span>
        </button>
      </div>

      <div id="candidates-table-container">
        <div style="text-align: center; padding: 30px; color: var(--text-muted);">
          Loading candidate matching results...
        </div>
      </div>
    </div>
  `;
}

async function handleRefreshRankings(jobId) {
  const btn = document.getElementById("btn-refresh-rankings");
  if (!btn) return;
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `
    <svg class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
    <span>Refreshing...</span>
  `;
  try {
    await loadCandidatesForJob(jobId, false);
    btn.classList.add("btn-refresh-success");
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>Updated!</span>
    `;
    showToast("Candidate rankings refreshed successfully", "success");
    setTimeout(() => {
      btn.classList.remove("btn-refresh-success");
      btn.innerHTML = originalHtml;
      btn.disabled = false;
    }, 1400);
  } catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast("Failed to refresh candidate rankings", "error");
  }
}

async function loadCandidatesForJob(jobId, showToastNotification = false) {
  try {
    const res = await fetch(`/jobs/${jobId}/candidates`);
    if (!res.ok) throw new Error("Failed to load candidates");
    const data = await res.json();
    
    const countBadge = document.getElementById("candidate-count-badge");
    if (countBadge) countBadge.textContent = data.total_candidates;

    metricTotalCandidates.textContent = data.total_candidates;
    if (data.candidates && data.candidates.length > 0) {
      metricTopScore.textContent = `${data.candidates[0].match_score}%`;
    } else {
      metricTopScore.textContent = "0%";
    }

    renderCandidatesTable(data.candidates);

    if (showToastNotification) {
      showToast(`Rankings updated (${data.candidates.length} candidates)`, "info");
    }
  } catch (err) {
    console.error("Error loading candidates:", err);
  }
}

function renderCandidatesTable(candidates) {
  const container = document.getElementById("candidates-table-container");
  if (!container) return;

  if (!candidates || candidates.length === 0) {
    container.innerHTML = `
      <div class="empty-candidates-box">
        <h4>No Candidates Evaluated Yet</h4>
        <p>
          Open the <strong>Candidate Matching Portal</strong>, select <code>${selectedJobId}</code>, and upload candidate resumes (.pdf, .docx, or .txt).
          Matching scores and ranked results will appear here automatically.
        </p>
      </div>
    `;
    return;
  }

  const rowsHtml = candidates.map(c => {
    let rankBadgeClass = "rank-other";
    if (c.rank === 1) rankBadgeClass = "rank-1";
    else if (c.rank === 2) rankBadgeClass = "rank-2";
    else if (c.rank === 3) rankBadgeClass = "rank-3";

    let scoreClass = "score-low";
    if (c.match_score >= 75) scoreClass = "score-high";
    else if (c.match_score >= 50) scoreClass = "score-med";

    const evalStatus = c.evaluation_status || "Evaluation Completed";
    const statusBadgeClass = evalStatus === "Review Flagged" ? "status-failed" : "status-synced";

    const evidenceText = c.evidence_summary || "Contextual assessment verified against requirements.";

    return `
      <tr>
        <td style="width: 44px; text-align: center;">
          <span class="rank-badge ${rankBadgeClass}">#${c.rank}</span>
        </td>
        <td>
          <div style="font-weight: 700; color: var(--text-primary);">${c.candidate_name}</div>
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: var(--text-muted);">${c.candidate_id}</div>
        </td>
        <td>
          <span class="score-pill ${scoreClass}">${c.match_score}%</span>
        </td>
        <td>
          <div style="font-weight: 600;">${c.extracted_experience} Yrs</div>
          <div style="font-size: 0.72rem; color: var(--text-secondary);">${c.experience_match_status}</div>
        </td>
        <td style="max-width: 240px; font-size: 0.8rem; line-height: 1.35; color: var(--text-secondary);">
          ${evidenceText}
        </td>
        <td>
          <span class="sync-status ${statusBadgeClass}">${evalStatus}</span>
        </td>
        <td style="font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap;">
          ${formatToIST(c.received_at)}
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="openCandidateDetails('${selectedJobId}', '${c.candidate_id}')" style="font-size: 0.75rem; padding: 4px 8px;">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join("");

  container.innerHTML = `
    <div class="candidates-table-wrap">
      <table class="candidates-table">
        <thead>
          <tr>
            <th style="text-align: center;">Rank</th>
            <th>Candidate</th>
            <th>Matching Score</th>
            <th>Experience</th>
            <th>Relevant Evidence Summary</th>
            <th>Evaluation Status</th>
            <th>Evaluated (IST)</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    </div>
  `;
}

async function openCandidateDetails(jobId, candidateId) {
  const modal = document.getElementById("modal-candidate-details");
  const body = document.getElementById("cand-detail-body");
  const title = document.getElementById("cand-detail-title");
  const subtitle = document.getElementById("cand-detail-subtitle");
  if (!modal || !body) return;

  body.innerHTML = "<div style='text-align:center; padding: 20px;'>Loading evaluation details...</div>";
  modal.classList.add("active");

  try {
    const res = await fetch(`/jobs/${jobId}/candidates/${candidateId}/details`);
    if (!res.ok) throw new Error("Could not retrieve candidate details");
    const d = await res.json();

    title.textContent = `${d.candidate_name} — Evaluation Details`;
    subtitle.textContent = `Candidate ID: ${d.candidate_id} | Job: ${d.job_id}`;

    const matchedBadges = (d.matched_skills && d.matched_skills.length > 0)
      ? d.matched_skills.map(s => `<span class="tag-matched" style="margin-right: 4px;">${s}</span>`).join("")
      : "<span style='color: var(--text-muted);'>None detected</span>";

    const missingBadges = (d.missing_skills && d.missing_skills.length > 0)
      ? d.missing_skills.map(s => `<span class="tag-missing" style="margin-right: 4px;">${s}</span>`).join("")
      : "<span style='color: var(--success-text);'>None (All verified)</span>";

    body.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
        <div style="background: var(--bg-surface); padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Match Score</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--brand-primary);">${d.match_score}%</div>
        </div>
        <div style="background: var(--bg-surface); padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Status</div>
          <div style="font-size: 1rem; font-weight: 700; color: ${d.evaluation_status === 'Review Flagged' ? 'var(--warning-text, #b45309)' : 'var(--success-text)}; margin-top: 4px;'>
            ${d.evaluation_status || 'Evaluation Completed'}
          </div>
        </div>
      </div>

      <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px; background: var(--bg-surface); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">
        <strong>Evaluation Received (IST):</strong> ${formatToIST(d.received_at)}
      </div>

      <div style="margin-bottom: 14px;">
        <div style="font-weight: 700; font-size: 0.85rem; margin-bottom: 4px;">Verified Contextual Evidence Summary</div>
        <p style="font-size: 0.85rem; line-height: 1.4; color: var(--text-secondary); background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          ${d.evidence_summary || "No specific evidence summary available."}
        </p>
      </div>

      <div style="margin-bottom: 12px;">
        <div style="font-weight: 700; font-size: 0.82rem; margin-bottom: 4px;">Experience Assessment</div>
        <div style="font-size: 0.82rem; color: var(--text-secondary);">
          <strong>${d.extracted_experience} Years</strong> — ${d.experience_match_status}
        </div>
      </div>

      <div style="margin-bottom: 12px;">
        <div style="font-weight: 700; font-size: 0.82rem; margin-bottom: 4px;">Matched Competencies</div>
        <div>${matchedBadges}</div>
      </div>

      <div>
        <div style="font-weight: 700; font-size: 0.82rem; margin-bottom: 4px;">Missing / Insufficient Evidence Skills</div>
        <div>${missingBadges}</div>
      </div>
    `;
  } catch (e) {
    body.innerHTML = `<div style="color: var(--danger-text); padding: 20px; text-align: center;">Error loading details: ${e.message}</div>`;
  }
}

// Modal closing setup
document.addEventListener("DOMContentLoaded", () => {
  const candModal = document.getElementById("modal-candidate-details");
  const closeBtn1 = document.getElementById("btn-close-candidate-modal");
  const closeBtn2 = document.getElementById("btn-close-cand-modal-foot");

  [closeBtn1, closeBtn2].forEach(b => {
    if (b) {
      b.addEventListener("click", () => {
        if (candModal) candModal.classList.remove("active");
      });
    }
  });

  if (candModal) {
    candModal.addEventListener("click", (e) => {
      if (e.target === candModal) candModal.classList.remove("active");
    });
  }
});

async function retrySyncJob(jobId) {
  try {
    showToast(`Synchronizing ${jobId} with Candidate Matching Portal...`, "info");
    const res = await fetch(`/jobs/${jobId}/sync`, { method: "POST" });
    const data = await res.json();
    if (res.ok && data.sync_status === "synced") {
      showToast(`Job ${jobId} synchronized successfully!`, "success");
    } else {
      showToast(`Sync failed: Candidate Matching Portal is currently unreachable`, "error");
    }
    loadJobs();
  } catch (err) {
    showToast("Sync request failed. Make sure Candidate Matching Portal is running.", "error");
  }
}

async function deleteJob(jobId) {
  if (!confirm(`Delete job ${jobId}?`)) return;
  try {
    const res = await fetch(`/jobs/${jobId}`, { method: "DELETE" });
    if (res.ok) {
      showToast(`Job ${jobId} deleted`, "success");
      selectedJobId = null;
      loadJobs();
    }
  } catch (err) {
    showToast("Failed to delete job", "error");
  }
}

async function handleCreateJob(e) {
  e.preventDefault();
  
  // 1. Auto-flush any pending text in the skill inputs
  addSkillTag(requiredInput, requiredSkillsList, requiredTagsContainer);
  addSkillTag(preferredInput, preferredSkillsList, preferredTagsContainer);

  // 2. Fallback: scrape any rendered tag elements to ensure nothing is missed
  const domReq = Array.from(requiredTagsContainer.querySelectorAll(".tag-badge span:first-child"))
    .map(s => s.textContent.trim()).filter(Boolean);
  domReq.forEach(s => { if (!requiredSkillsList.includes(s)) requiredSkillsList.push(s); });

  const domPref = Array.from(preferredTagsContainer.querySelectorAll(".tag-badge span:first-child"))
    .map(s => s.textContent.trim()).filter(Boolean);
  domPref.forEach(s => { if (!preferredSkillsList.includes(s)) preferredSkillsList.push(s); });

  // 3. Validation
  if (requiredSkillsList.length === 0) {
    alert("Please add at least one required skill (type skill and press Enter or click + Add).");
    requiredInput.focus();
    return;
  }

  const submitBtn = document.getElementById("btn-submit-job");
  const spinner = document.getElementById("submit-spinner");
  submitBtn.disabled = true;
  spinner.classList.remove("hide");

  const formData = new FormData(createJobForm);
  const payload = {
    job_id: formData.get("job_id").trim(),
    job_title: formData.get("job_title").trim(),
    job_description: formData.get("job_description").trim(),
    required_skills: [...requiredSkillsList],
    preferred_skills: [...preferredSkillsList],
    min_experience: parseFloat(formData.get("min_experience")),
    education_requirement: formData.get("education_requirement").trim()
  };

  try {
    const res = await fetch("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create job");
    }

    const created = await res.json();
    closeJobModal();
    
    if (created.sync_status === "synced") {
      showToast(`Job ${created.job_id} posted and synchronized with Candidate Matching Portal!`, "success");
    } else {
      showToast(`Job ${created.job_id} posted locally (Sync status: ${created.sync_status})`, "info");
    }

    await loadJobs();
    selectJob(created.job_id);
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submitBtn.disabled = false;
    spinner.classList.add("hide");
  }
}

function openJobModal() {
  createJobForm.reset();
  // Clear arrays in place to preserve closures and references
  requiredSkillsList.length = 0;
  preferredSkillsList.length = 0;
  renderTags(requiredSkillsList, requiredTagsContainer);
  renderTags(preferredSkillsList, preferredTagsContainer);
  modalCreateJob.classList.add("open");
}

function closeJobModal() {
  modalCreateJob.classList.remove("open");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Global functions for inline HTML event handlers
window.retrySyncJob = retrySyncJob;
window.deleteJob = deleteJob;
window.loadCandidatesForJob = loadCandidatesForJob;
window.handleRefreshRankings = handleRefreshRankings;


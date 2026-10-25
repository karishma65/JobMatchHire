// State
let receivedJobs = [];
let selectedJob = null;
let currentFile = null;

// DOM Elements
const selectJob = document.getElementById("select-job");
const jobSummaryCard = document.getElementById("job-summary-card");

const dropzone = document.getElementById("dropzone");
const resumeFileInput = document.getElementById("resume-file-input");
const selectedFilePill = document.getElementById("selected-file-pill");
const fileNameText = document.getElementById("file-name-text");
const fileSizeText = document.getElementById("file-size-text");
const btnClearFile = document.getElementById("btn-clear-file");
const inputCandidateName = document.getElementById("input-candidate-name");

const btnAnalyzeResume = document.getElementById("btn-analyze-resume");
const analyzeSpinner = document.getElementById("analyze-spinner");
const resultsDisplayArea = document.getElementById("results-display-area");

const btnRefreshJobs = document.getElementById("btn-refresh-jobs");

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadReceivedJobs();
  restoreCandidateSession();
});

function restoreCandidateSession() {
  try {
    const saved = sessionStorage.getItem("jmh_candidate_eval");
    if (saved) {
      const data = JSON.parse(saved);
      renderAnalysisResult(data);
    }
  } catch (e) {
    console.debug("No active candidate session to restore.");
  }
}

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

function setupEventListeners() {
  btnRefreshJobs.addEventListener("click", async () => {
    btnRefreshJobs.disabled = true;
    showToast("Syncing latest job postings from Recruiter Portal...", "info");
    await loadReceivedJobs();
    btnRefreshJobs.disabled = false;
    showToast(`Refreshed: ${receivedJobs.length} active job(s) available`, "success");
  });

  selectJob.addEventListener("change", (e) => {
    const jId = e.target.value;
    selectedJob = receivedJobs.find(j => j.job_id === jId) || null;
    renderJobSummary(selectedJob);
  });

  // Dedicated file picker opener function to guarantee Windows file dialog opens
  function openFilePicker(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    resumeFileInput.value = "";
    resumeFileInput.click();
  }

  // Dropzone click & keyboard activation
  dropzone.addEventListener("click", openFilePicker);
  const browseLink = document.getElementById("browse-link") || document.querySelector(".browse-link");
  if (browseLink) {
    browseLink.addEventListener("click", openFilePicker);
  }
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      openFilePicker(e);
    }
  });

  // Drag & drop support
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  resumeFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  btnClearFile.addEventListener("click", clearSelectedFile);

  // Main Action
  btnAnalyzeResume.addEventListener("click", handleAnalyzeResume);
}

async function loadReceivedJobs() {
  try {
    const res = await fetch("/jobs?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load jobs");
    receivedJobs = await res.json();

    const previousSelectedId = selectJob.value || (selectedJob ? selectedJob.job_id : "");
    selectJob.innerHTML = '<option value="">Select a job</option>';

    if (receivedJobs.length === 0) {
      selectedJob = null;
      jobSummaryCard.innerHTML = `
        <div class="empty-hint" style="color: var(--text-secondary);">
          No active job requirements found.<br>
          Please create a job in <strong>Recruiter Portal (http://127.0.0.1:8000)</strong> first, then click <strong>Refresh Jobs</strong>.
        </div>
      `;
      return;
    }

    receivedJobs.forEach(job => {
      const opt = document.createElement("option");
      opt.value = job.job_id;
      // Requirement: Display only the job ID and job title in each option
      opt.textContent = `${job.job_id} - ${job.job_title}`;
      selectJob.appendChild(opt);
    });

    if (previousSelectedId && receivedJobs.some(j => j.job_id === previousSelectedId)) {
      selectJob.value = previousSelectedId;
      selectedJob = receivedJobs.find(j => j.job_id === previousSelectedId);
      renderJobSummary(selectedJob);
    } else {
      selectJob.value = "";
      selectedJob = null;
      renderJobSummary(null);
    }
  } catch (err) {
    console.error("Error loading jobs:", err);
    showToast("Could not load jobs from Recruiter Portal", "error");
  }
}

function renderJobSummary(job) {
  if (!job) {
    jobSummaryCard.innerHTML = `<div class="empty-hint">Select a job from the dropdown to view its criteria.</div>`;
    return;
  }

  const reqHtml = job.required_skills && job.required_skills.length > 0
    ? job.required_skills.map(s => `<span class="chip-mini" style="border-color: #BFDBFE; color: var(--primary);">${s}</span>`).join("")
    : '<span style="color: var(--text-muted); font-size: 0.75rem;">None</span>';

  const prefHtml = job.preferred_skills && job.preferred_skills.length > 0
    ? job.preferred_skills.map(s => `<span class="chip-mini">${s}</span>`).join("")
    : '<span style="color: var(--text-muted); font-size: 0.75rem;">None</span>';

  jobSummaryCard.innerHTML = `
    <div class="summary-title">${job.job_title} <span style="font-family: 'JetBrains Mono'; font-size: 0.75rem; color: var(--primary);">[${job.job_id}]</span></div>
    <div class="summary-meta">
      <span><strong>Min Experience:</strong> ${job.min_experience} Years</span>
      <span>•</span>
      <span><strong>Education:</strong> ${job.education_requirement}</span>
      ${job.received_at ? `<span>•</span><span><strong>Synced (IST):</strong> ${formatToIST(job.received_at)}</span>` : ''}
    </div>
    <div class="summary-skills-label">Required Skills:</div>
    <div class="summary-skills-chips">${reqHtml}</div>
    <div class="summary-skills-label" style="margin-top: 6px;">Preferred Skills:</div>
    <div class="summary-skills-chips">${prefHtml}</div>
  `;
}

function handleFileSelected(file) {
  if (!file) return;

  const validExts = [".pdf", ".docx", ".doc", ".txt"];
  const fileExt = "." + file.name.split(".").pop().toLowerCase();
  if (!validExts.includes(fileExt)) {
    showToast("Unsupported file format. Please upload a PDF, DOCX, or TXT file.", "error");
    clearSelectedFile();
    return;
  }

  currentFile = file;
  fileNameText.textContent = file.name;
  fileSizeText.textContent = `(${formatBytes(file.size)})`;

  dropzone.classList.add("hide");
  selectedFilePill.classList.remove("hide");
  showToast(`File selected: ${file.name}`, "info");
}

function clearSelectedFile() {
  currentFile = null;
  resumeFileInput.value = "";
  selectedFilePill.classList.add("hide");
  dropzone.classList.remove("hide");
}

function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

async function handleAnalyzeResume() {
  if (!selectedJob) {
    alert("Please select a target job opening from the dropdown.");
    selectJob.focus();
    return;
  }

  if (!currentFile) {
    alert("Please upload a resume file (.pdf, .docx, or .txt).");
    return;
  }

  btnAnalyzeResume.disabled = true;
  analyzeSpinner.classList.remove("hide");

  const formData = new FormData();
  formData.append("job_id", selectedJob.job_id);
  formData.append("resume_file", currentFile);

  const customName = inputCandidateName.value.trim();
  if (customName) {
    formData.append("candidate_name", customName);
  }

  // Include candidate ID for re-evaluation versioning if available
  const existingCandId = sessionStorage.getItem("jmh_active_cand_id");
  if (existingCandId) {
    formData.append("candidate_id", existingCandId);
  }

  try {
    const res = await fetch("/analyze-resume", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Analysis failed");
    }

    const data = await res.json();
    // Save current candidate session so only this candidate sees their evaluation
    try {
      sessionStorage.setItem("jmh_candidate_eval", JSON.stringify(data));
      sessionStorage.setItem("jmh_active_cand_id", data.candidate_id);
    } catch (e) {}

    renderAnalysisResult(data);
    showToast(`Evaluation completed. Match Score: ${data.match_score}%`, "success");
  } catch (err) {
    console.error("Error analyzing resume:", err);
    showToast(err.message || "Failed to analyze resume", "error");
  } finally {
    btnAnalyzeResume.disabled = false;
    analyzeSpinner.classList.add("hide");
  }
}

function renderAnalysisResult(result) {
  const downloadUrl = result.report_download_url || `/candidates/${result.candidate_id}/report?token=${result.candidate_token}`;
  const evalStatus = result.evaluation_status || "Evaluation Completed";
  const statusColor = evalStatus === "Review Flagged" ? "var(--warning-text, #b45309)" : "var(--success-text, #15803d)";

  resultsDisplayArea.innerHTML = `
    <div class="card" style="padding: 24px; border: 1px solid var(--border-color); background: var(--bg-surface); border-radius: 8px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px;">
        <div>
          <span style="font-size: 0.75rem; font-family: 'JetBrains Mono'; background: var(--border-color); padding: 3px 8px; border-radius: 4px; color: var(--text-secondary); text-transform: uppercase;">
            Target Job: ${result.job_id}
          </span>
          <h2 style="margin: 8px 0 4px; font-size: 1.4rem; color: var(--text-primary);">${result.candidate_name}</h2>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">
            Candidate Identifier: <code style="font-family: 'JetBrains Mono'; font-weight: 700; color: var(--brand-primary);">${result.candidate_id}</code>
            <span style="margin: 0 6px;">•</span>
            Resume Version: <span class="tag-version" style="background: var(--brand-primary); color: #fff; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">v${result.resume_version || 1}</span>
            <span style="margin: 0 6px;">•</span>
            Evaluated (IST): <span style="font-weight: 600; color: var(--text-primary);">${formatToIST(result.created_at)}</span>
          </div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 2.2rem; font-weight: 800; color: var(--brand-primary); font-family: 'JetBrains Mono'; line-height: 1;">
            ${result.match_score}%
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-top: 4px;">Overall Match Score</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px;">
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 14px; border-radius: 6px;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Evaluation Status</div>
          <div style="font-size: 0.95rem; font-weight: 700; color: ${statusColor}; margin-top: 3px;">
            ${evalStatus}
          </div>
        </div>
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 14px; border-radius: 6px;">
          <div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Experience Assessment</div>
          <div style="font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin-top: 3px;">
            ${result.extracted_experience} Years (${result.experience_match_status})
          </div>
        </div>
      </div>

      <div style="background: #f1f5f9; border-left: 4px solid var(--brand-primary); padding: 12px 14px; border-radius: 4px; margin-bottom: 20px;">
        <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">
          Contextual Evidence Summary
        </div>
        <p style="margin: 0; font-size: 0.85rem; color: var(--text-primary); line-height: 1.4;">
          ${result.evidence_summary || "ECCE completed contextual parsing of skills and professional experience."}
        </p>
      </div>

      <!-- Action Section: Download PDF Report and Re-evaluation -->
      <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 16px;">
        <a href="${downloadUrl}" target="_blank" class="btn btn-primary" id="btn-download-pdf" style="display: inline-flex; align-items: center; gap: 8px; text-decoration: none; padding: 10px 20px; font-weight: 700;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Download Evaluation Report (PDF)
        </a>
        <button type="button" class="btn btn-outline" id="btn-reevaluate" onclick="prepareReevaluation('${result.candidate_name}', '${result.candidate_id}')" style="display: inline-flex; align-items: center; gap: 6px; padding: 10px 16px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          Upload Updated Resume / Re-evaluate
        </button>
      </div>

      <div style="font-size: 0.76rem; color: var(--text-muted); line-height: 1.45; border-top: 1px solid var(--border-color); padding-top: 12px;">
        <strong>Candidate Privacy & Access Notice:</strong> In accordance with candidate privacy requirements, the full 8-section breakdown (including contextual resume passages, hypothetical counterfactual simulations, and private skill-gap remediation guidance) is compiled into your individual, downloadable PDF report. This report is protected by your candidate session token.
      </div>
    </div>
  `;
}

function prepareReevaluation(candName, candId) {
  clearSelectedFile();
  if (candName && inputCandidateName) {
    inputCandidateName.value = candName;
  }
  if (candId) {
    sessionStorage.setItem("jmh_active_cand_id", candId);
  }
  showToast("Ready for re-evaluation. Select an updated resume file to submit a revised version.", "info");
  if (dropzone) {
    dropzone.scrollIntoView({ behavior: "smooth" });
  }
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

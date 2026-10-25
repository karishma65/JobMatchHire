// ==========================================================================
// JobMatchHire - Recruiter Suite Landing Script
// Fluid Agency Cursor & Live Requisition Intelligence Monitoring
// ==========================================================================

// Fluid Agency Cursor (eDesign Interactive Signature)
function initCustomCursor() {
  const dot = document.getElementById("cursorDot");
  const ring = document.getElementById("cursorRing");
  if (!dot || !ring) return;

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let ringX = mouseX;
  let ringY = mouseY;

  window.addEventListener("mousemove", (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0) translate(-50%, -50%)`;
  });

  function renderFollower() {
    ringX += (mouseX - ringX) * 0.18;
    ringY += (mouseY - ringY) * 0.18;
    ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%)`;
    requestAnimationFrame(renderFollower);
  }
  requestAnimationFrame(renderFollower);

  // Dynamic hover delegation on interactive elements
  document.addEventListener("mouseover", (e) => {
    if (e.target.closest("a, button, .showcase-card, .btn-pill, .stat-item, .workflow-step-card")) {
      ring.classList.add("cursor-hover");
    }
  });

  document.addEventListener("mouseout", (e) => {
    if (e.target.closest("a, button, .showcase-card, .btn-pill, .stat-item, .workflow-step-card")) {
      ring.classList.remove("cursor-hover");
    }
  });
}

// Live Requisitions & Candidate Metrics
async function loadLiveRecruiterMetrics() {
  const statJobCount = document.getElementById("stat-job-count");
  const statCandCount = document.getElementById("stat-cand-count");
  const statTopScore = document.getElementById("stat-top-score");
  const statEngineStatus = document.getElementById("stat-engine-status");

  try {
    const res = await fetch("/jobs?t=" + Date.now(), { cache: "no-store" });
    if (res.ok) {
      const jobs = await res.json();
      if (statJobCount) statJobCount.textContent = jobs.length;

      const totalCandidates = jobs.reduce((sum, j) => sum + (j.candidate_count || 0), 0);
      if (statCandCount) statCandCount.textContent = totalCandidates;

      const topScore = Math.max(0, ...jobs.map(j => j.top_score || 0));
      if (statTopScore) statTopScore.textContent = topScore > 0 ? `${topScore.toFixed(1)}%` : "0%";

      if (statEngineStatus) {
        statEngineStatus.textContent = "ACTIVE";
        statEngineStatus.style.color = "var(--accent-green)";
      }
    }
  } catch (err) {
    console.debug("Metrics fetch error:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initCustomCursor();
  loadLiveRecruiterMetrics();
  setInterval(loadLiveRecruiterMetrics, 6000);
});

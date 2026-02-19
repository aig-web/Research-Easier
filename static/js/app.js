/* ── Research Easier — Frontend Logic ─────────────────────────────────── */

let currentTaskId = null;
let pollTimer = null;
let sentimentChart = null;
let resultData = null;

/* ── URL detection ───────────────────────────────────────────────────── */

const PLATFORMS = {
  instagram: /instagram\.com|instagr\.am/i,
  twitter:   /twitter\.com|x\.com/i,
  threads:   /threads\.net/i,
  youtube:   /youtube\.com|youtu\.be/i,
  tiktok:    /tiktok\.com/i,
  facebook:  /facebook\.com|fb\.watch/i,
  reddit:    /reddit\.com|redd\.it/i,
};

document.getElementById("urlInput").addEventListener("input", (e) => {
  const url = e.target.value.trim();
  const badge = document.getElementById("platformBadge");
  if (!url) { badge.classList.add("hidden"); return; }

  let detected = "Other";
  for (const [name, re] of Object.entries(PLATFORMS)) {
    if (re.test(url)) { detected = name.charAt(0).toUpperCase() + name.slice(1); break; }
  }
  badge.textContent = `Platform: ${detected}`;
  badge.classList.remove("hidden");

  // Show / hide comment step
  const commentStep = document.querySelector('.step[data-step="fetching_comments"]');
  const analyseStep = document.querySelector('.step[data-step="analysing"]');
  const isInsta = /instagram\.com|instagr\.am/i.test(url);
  commentStep.style.display = isInsta ? "flex" : "none";
  analyseStep.style.display = isInsta ? "flex" : "none";
});

/* ── Start processing ────────────────────────────────────────────────── */

async function startProcessing() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) return;

  const btn = document.getElementById("processBtn");
  btn.disabled = true;
  btn.querySelector(".btn-text").textContent = "Processing…";
  btn.querySelector(".btn-loader").classList.remove("hidden");

  hideEl("errorSection");
  hideEl("resultsSection");
  showEl("progressSection");
  resetProgress();

  const body = {
    url,
    model_size:     document.getElementById("modelSize").value,
    language:       document.getElementById("language").value,
    insta_username: document.getElementById("instaUser").value,
    insta_password: document.getElementById("instaPass").value,
    max_comments:   parseInt(document.getElementById("maxComments").value, 10),
    cookies_file:   document.getElementById("cookiesFile").value,
  };

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    currentTaskId = data.task_id;
    pollTimer = setInterval(pollStatus, 1000);
  } catch (err) {
    showError(err.message);
    resetBtn();
  }
}

/* ── Poll for status ─────────────────────────────────────────────────── */

async function pollStatus() {
  if (!currentTaskId) return;
  try {
    const res = await fetch(`/api/status/${currentTaskId}`);
    const data = await res.json();

    updateProgress(data.progress, data.message, data.step);

    if (data.status === "complete") {
      clearInterval(pollTimer);
      resultData = data.result;
      renderResults(data.result);
      resetBtn();
    } else if (data.status === "error") {
      clearInterval(pollTimer);
      showError(data.error || "Processing failed");
      resetBtn();
    }
  } catch (err) {
    // Network hiccup — keep polling
  }
}

/* ── Progress UI ─────────────────────────────────────────────────────── */

const STEP_ORDER = ["downloading", "transcribing", "fetching_comments", "analysing", "done"];

function resetProgress() {
  updateProgress(0, "Starting…", "queued");
  document.querySelectorAll(".step").forEach((s) => {
    s.classList.remove("active", "done");
  });
}

function updateProgress(pct, msg, step) {
  document.getElementById("progressBar").style.width = pct + "%";
  document.getElementById("progressPct").textContent = pct + "%";
  document.getElementById("progressMsg").textContent = msg;

  const stepIdx = STEP_ORDER.indexOf(step);
  document.querySelectorAll(".step").forEach((el) => {
    const elStep = el.dataset.step;
    const elIdx = STEP_ORDER.indexOf(elStep);
    el.classList.remove("active", "done");
    if (elIdx < stepIdx) el.classList.add("done");
    else if (elIdx === stepIdx) el.classList.add("active");
  });
}

/* ── Render results ──────────────────────────────────────────────────── */

function renderResults(result) {
  hideEl("progressSection");
  showEl("resultsSection");

  // Video
  const video = result.video;
  if (video) {
    document.getElementById("videoPlayer").src = video.video_url;
    document.getElementById("videoTitle").textContent = video.title || "Video";
    document.getElementById("chipPlatform").textContent = (video.platform || "video").charAt(0).toUpperCase() + (video.platform || "").slice(1);
    document.getElementById("chipUploader").textContent = video.uploader || "";
    if (video.duration) {
      const m = Math.floor(video.duration / 60);
      const s = Math.floor(video.duration % 60);
      document.getElementById("chipDuration").textContent = `${m}m ${s}s`;
    }
  }

  // Tabs visibility
  const hasSentiment = result.is_instagram && result.sentiment;
  document.getElementById("tabSentiment").style.display = hasSentiment ? "block" : "none";

  // Transcription
  const trans = result.transcription;
  if (trans) {
    document.getElementById("transcriptText").textContent = trans.formatted;
    document.getElementById("langInfo").textContent =
      `Language: ${trans.language} (confidence: ${(trans.language_probability * 100).toFixed(0)}%)`;
    hideEl("noTranscription");
  } else {
    showEl("noTranscription");
    document.getElementById("transcriptText").textContent = "";
  }

  // Sentiment
  if (hasSentiment) {
    renderSentiment(result.sentiment);
    hideEl("noSentiment");
  } else {
    showEl("noSentiment");
    hideEl("sentimentContent");
  }

  // Key points
  renderKeyPoints(result);

  // Default tab
  switchTab("transcription");
}

/* ── Transcription helpers ───────────────────────────────────────────── */

function toggleTimestamps() {
  if (!resultData || !resultData.transcription) return;
  const show = document.getElementById("showTimestamps").checked;
  document.getElementById("transcriptText").textContent =
    show ? resultData.transcription.formatted : resultData.transcription.formatted_plain;
}

function downloadTranscription() {
  if (!resultData || !resultData.transcription) return;
  const text = resultData.transcription.formatted;
  const blob = new Blob([text], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "transcription.txt";
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ── Sentiment chart ─────────────────────────────────────────────────── */

function renderSentiment(sentiment) {
  showEl("sentimentContent");
  document.getElementById("sentimentSummary").textContent = sentiment.summary;

  const dist = sentiment.distribution;
  const total = dist.Positive + dist.Negative + dist.Neutral;
  document.getElementById("statPositive").textContent = dist.Positive;
  document.getElementById("statNegative").textContent = dist.Negative;
  document.getElementById("statNeutral").textContent  = dist.Neutral;
  document.getElementById("statTotal").textContent     = total;

  // Chart
  if (sentimentChart) sentimentChart.destroy();
  const ctx = document.getElementById("sentimentChart").getContext("2d");
  sentimentChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Positive", "Negative", "Neutral"],
      datasets: [{
        data: [dist.Positive, dist.Negative, dist.Neutral],
        backgroundColor: ["#2ecc71", "#e74c3c", "#95a5a6"],
        borderWidth: 0,
      }],
    },
    options: {
      cutout: "60%",
      plugins: {
        legend: { display: true, position: "bottom", labels: { color: "#e2e2ef", padding: 16 } },
      },
      responsive: true,
      maintainAspectRatio: true,
    },
  });

  // Comments
  renderCommentList("positiveComments", sentiment.most_positive);
  renderCommentList("negativeComments", sentiment.most_negative);
}

function renderCommentList(containerId, comments) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  if (!comments || !comments.length) {
    container.innerHTML = '<p class="empty-state">No comments</p>';
    return;
  }
  comments.forEach((c) => {
    const div = document.createElement("div");
    div.className = "comment-card";
    div.innerHTML = `
      <span class="comment-owner">@${esc(c.owner || "user")}</span>
      ${c.likes ? `<span class="comment-likes">${c.likes} likes</span>` : ""}
      <span class="comment-sentiment ${c.sentiment}">[${c.sentiment}]</span>
      <div class="comment-text">${esc(c.text)}</div>
    `;
    container.appendChild(div);
  });
}

/* ── Key points ──────────────────────────────────────────────────────── */

function renderKeyPoints(result) {
  const hasCommentKP = result.key_points && result.key_points.key_phrases && result.key_points.key_phrases.length;
  const hasTransKP   = result.transcription_key_points && result.transcription_key_points.key_phrases && result.transcription_key_points.key_phrases.length;

  if (!hasCommentKP && !hasTransKP) {
    showEl("noKeypoints");
    hideEl("keypointsContent");
    return;
  }

  showEl("keypointsContent");
  hideEl("noKeypoints");

  // Comment key points
  if (hasCommentKP) {
    showEl("commentKeyPoints");
    fillList("commentSummaryPoints", result.key_points.summary_points);
    fillPhrases("topPhrases", result.key_points.key_phrases);
    fillThemes("commonThemes", result.key_points.common_themes);
  } else {
    hideEl("commentKeyPoints");
  }

  // Transcript key points
  if (hasTransKP) {
    showEl("transcriptKeyPoints");
    fillList("transcriptSummaryPoints", result.transcription_key_points.summary_points);
    fillPhrases("transcriptPhrases", result.transcription_key_points.key_phrases);
  } else {
    hideEl("transcriptKeyPoints");
  }
}

function fillList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  (items || []).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    ul.appendChild(li);
  });
}

function fillPhrases(id, phrases) {
  const container = document.getElementById(id);
  container.innerHTML = "";
  (phrases || []).forEach((p) => {
    const span = document.createElement("span");
    span.className = "phrase-chip";
    span.innerHTML = `${esc(p.phrase)} <span class="phrase-score">${p.score}</span>`;
    container.appendChild(span);
  });
}

function fillThemes(id, themes) {
  const container = document.getElementById(id);
  container.innerHTML = "";
  (themes || []).forEach((t) => {
    const span = document.createElement("span");
    span.className = "phrase-chip";
    span.innerHTML = `${esc(t.word)} <span class="phrase-score">${t.count}x</span>`;
    container.appendChild(span);
  });
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
  document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add("active");
  document.getElementById(`pane-${tabName}`).classList.add("active");
}

/* ── Helpers ──────────────────────────────────────────────────────────── */

function showEl(id)  { document.getElementById(id).classList.remove("hidden"); }
function hideEl(id)  { document.getElementById(id).classList.add("hidden"); }

function resetBtn() {
  const btn = document.getElementById("processBtn");
  btn.disabled = false;
  btn.querySelector(".btn-text").textContent = "Process";
  btn.querySelector(".btn-loader").classList.add("hidden");
}

function showError(msg) {
  document.getElementById("errorMsg").textContent = msg;
  showEl("errorSection");
  hideEl("progressSection");
}

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

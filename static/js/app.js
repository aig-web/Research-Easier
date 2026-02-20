document.addEventListener("DOMContentLoaded", () => {
    const urlInput = document.getElementById("tweet-url");
    const analyzeBtn = document.getElementById("analyze-btn");
    const statusMsg = document.getElementById("status-msg");
    const loading = document.getElementById("loading");
    const ideasGrid = document.getElementById("ideas-grid");
    const emptyState = document.getElementById("empty-state");
    const weeklyView = document.getElementById("weekly-view");
    const categoriesView = document.getElementById("categories-view");

    // Tab switching
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");

            if (tab.dataset.tab === "weekly" || tab.dataset.tab === "categories") {
                loadWeeklyData();
            }
        });
    });

    // Analyze button
    analyzeBtn.addEventListener("click", analyze);
    urlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") analyze();
    });

    async function analyze() {
        const url = urlInput.value.trim();
        if (!url) return;

        hideStatus();
        loading.classList.remove("hidden");
        analyzeBtn.disabled = true;

        try {
            const res = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });

            const data = await res.json();

            if (!res.ok || data.error) {
                showStatus(data.error || "Analysis failed", "error");
                return;
            }

            showStatus("Tweet analyzed and added to dashboard!", "success");
            urlInput.value = "";
            loadIdeas();
        } catch (err) {
            showStatus(`Network error: ${err.message}`, "error");
        } finally {
            loading.classList.add("hidden");
            analyzeBtn.disabled = false;
        }
    }

    function showStatus(msg, type) {
        statusMsg.textContent = msg;
        statusMsg.className = `status-msg ${type}`;
        statusMsg.classList.remove("hidden");
        setTimeout(() => statusMsg.classList.add("hidden"), 5000);
    }

    function hideStatus() {
        statusMsg.classList.add("hidden");
    }

    // Load all ideas
    async function loadIdeas() {
        try {
            const res = await fetch("/api/ideas");
            const data = await res.json();
            renderIdeas(data.ideas || []);
        } catch (err) {
            console.error("Failed to load ideas:", err);
        }
    }

    function renderIdeas(ideas) {
        if (!ideas.length) {
            ideasGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">&#128269;</div>
                    <p>No ideas tracked yet. Paste a tweet link above to get started.</p>
                </div>`;
            return;
        }

        ideasGrid.innerHTML = ideas.map(idea => `
            <div class="idea-card" data-id="${idea.id}">
                <div class="card-header">
                    <div class="card-topic">${esc(idea.topic_name || "Untitled")}</div>
                    <span class="card-category">${esc(idea.category || "Other")}</span>
                </div>
                <div class="card-summary">${esc(idea.summary || idea.tweet_text || "")}</div>
                ${idea.has_video && idea.video_analysis ? `
                    <div class="card-video-analysis">
                        <span class="label">Video Analysis</span>
                        ${esc(idea.video_analysis)}
                    </div>` : ""}
                <div class="card-meta">
                    <span class="meta-item">
                        <span class="icon">&#128100;</span>
                        ${esc(idea.author || idea.author_handle || "Unknown")}
                    </span>
                    <span class="meta-item">
                        <span class="icon">&#128197;</span>
                        ${esc(idea.tweet_date || "N/A")}
                    </span>
                    <span class="meta-item">
                        <span class="icon">&#128065;</span>
                        ${esc(String(idea.view_count || "N/A"))}
                    </span>
                    ${idea.has_video ? `<span class="meta-item"><span class="icon">&#127909;</span> Video</span>` : ""}
                    <a class="card-link" href="${esc(idea.tweet_url)}" target="_blank" rel="noopener">${esc(idea.tweet_url)}</a>
                    <span class="card-actions">
                        <button class="delete-btn" onclick="deleteIdea(${idea.id})">Delete</button>
                    </span>
                </div>
            </div>
        `).join("");
    }

    // Weekly data
    async function loadWeeklyData() {
        try {
            const res = await fetch("/api/ideas/weekly");
            const data = await res.json();
            renderWeekly(data.weekly || {});
            renderCategories(data.categories || []);
        } catch (err) {
            console.error("Failed to load weekly data:", err);
        }
    }

    function renderWeekly(weekly) {
        const weeks = Object.keys(weekly);
        if (!weeks.length) {
            weeklyView.innerHTML = `<div class="empty-state"><p>No data yet.</p></div>`;
            return;
        }

        weeklyView.innerHTML = weeks.map(week => `
            <div class="week-group">
                <div class="week-header">
                    <span>Week: ${esc(week)}</span>
                    <span class="week-count">${weekly[week].length} idea${weekly[week].length !== 1 ? "s" : ""}</span>
                </div>
                <div class="week-ideas">
                    <div class="week-idea-row" style="font-weight:600;color:var(--text-muted);font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">
                        <div>Topic</div>
                        <div>Category</div>
                        <div style="text-align:center">Date</div>
                        <div style="text-align:center">Views</div>
                    </div>
                    ${weekly[week].map(idea => `
                        <div class="week-idea-row">
                            <div>
                                <div class="row-topic">${esc(idea.topic_name || "Untitled")}</div>
                                <div class="row-summary">${esc(idea.summary || "")}</div>
                            </div>
                            <div class="row-category">${esc(idea.category || "Other")}</div>
                            <div class="row-date">${esc(idea.tweet_date || "N/A")}</div>
                            <div class="row-views">${esc(String(idea.view_count || "N/A"))}</div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `).join("");
    }

    function renderCategories(categories) {
        if (!categories.length) {
            categoriesView.innerHTML = `<div class="empty-state"><p>No categories yet.</p></div>`;
            return;
        }

        categoriesView.innerHTML = categories.map(cat => `
            <div class="category-card">
                <div class="category-name">${esc(cat.category)}</div>
                <div class="category-count">${cat.count}</div>
                <div class="category-label">ideas</div>
            </div>
        `).join("");
    }

    // Delete idea
    window.deleteIdea = async function(id) {
        try {
            await fetch(`/api/ideas/${id}`, { method: "DELETE" });
            loadIdeas();
            loadWeeklyData();
        } catch (err) {
            console.error("Delete failed:", err);
        }
    };

    // Escape HTML
    function esc(str) {
        const div = document.createElement("div");
        div.textContent = str || "";
        return div.innerHTML;
    }

    // Initial load
    loadIdeas();
});

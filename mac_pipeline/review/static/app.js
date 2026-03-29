const state = {
  session: null,
  currentItem: null,
};

async function loadSession() {
  const response = await fetch("/api/session");
  state.session = await response.json();
  const nextItem = state.session.items.find((item) => !item.rated) || null;
  state.currentItem = nextItem;
  render();
}

function render() {
  const session = state.session;
  if (!session) {
    return;
  }
  const sampleMode = session.session_type === "sample_review";
  renderModeCopy(sampleMode);
  renderButtons(sampleMode);
  document.getElementById("sessionName").textContent = session.session_name;
  document.getElementById("remainingCount").textContent = `${session.remaining} remaining`;
  document.getElementById("progressValue").textContent = `${session.rated} / ${session.total}`;
  document.getElementById("progressCaption").textContent =
    session.remaining === 0
      ? "Review queue complete."
      : sampleMode
        ? "Use keyboard shortcuts P, R, or S."
        : "Use keyboard shortcuts A, B, G, X, or S.";

  const item = state.currentItem;
  if (!item) {
    document.getElementById("caseId").textContent = sampleMode ? "All samples reviewed" : "All comparisons reviewed";
    document.getElementById("promptText").textContent =
      "The session is complete. Ratings are stored in ratings.jsonl inside the review session folder.";
    document.getElementById("tagText").textContent = "";
    document.getElementById("videoGrid").innerHTML = "";
    return;
  }

  document.getElementById("caseId").textContent = item.case_id;
  document.getElementById("promptText").textContent = item.prompt || "Prompt unavailable for this case.";
  document.getElementById("tagText").textContent = sampleMode && item.tags?.length
    ? item.tags.join(" · ")
    : "";
  const grid = document.getElementById("videoGrid");
  grid.innerHTML = "";
  item.options.forEach((option) => grid.appendChild(buildOptionCard(option)));
}

function renderModeCopy(sampleMode) {
  document.getElementById("eyebrowText").textContent = sampleMode ? "Dataset curation surface" : "Blind evaluation surface";
  document.getElementById("heroTitle").textContent = sampleMode
    ? "Review rendered dataset samples before they enter training."
    : "Rate rendered Manim pairs without seeing the source model.";
  document.getElementById("heroLede").textContent = sampleMode
    ? "Watch each sample, decide whether it deserves promotion into the training set, and reject weak scenes before the model ever learns them."
    : "Compare A vs B, mark both-good or both-bad when needed, and keep the ratings as clean training signal instead of gut-feel notes.";
}

function renderButtons(sampleMode) {
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.hidden = button.dataset.mode !== (sampleMode ? "sample_review" : "blind_pair");
  });
}

function buildOptionCard(option) {
  const card = document.createElement("article");
  card.className = "option-card";
  const heading = document.createElement("h3");
  heading.textContent = option.slot === "sample" ? "Rendered sample" : `Option ${option.slot}`;
  card.appendChild(heading);

  if (option.video_url) {
    const video = document.createElement("video");
    video.src = option.video_url;
    video.controls = true;
    video.loop = true;
    video.preload = "metadata";
    card.appendChild(video);
  } else {
    const error = document.createElement("div");
    error.className = "error-block";
    error.textContent = "No rendered video is available for this option.";
    card.appendChild(error);
  }

  if (!option.render_ok) {
    const error = document.createElement("div");
    error.className = "error-block";
    error.textContent = option.render_log_tail || "Render failed.";
    card.appendChild(error);
  }
  return card;
}

async function submitVerdict(verdict) {
  if (!state.currentItem) {
    return;
  }
  const sampleMode = state.session.session_type === "sample_review";
  const payload = {
    review_id: state.currentItem.review_id,
    confidence: document.getElementById("confidence").value,
    notes: document.getElementById("notes").value,
    session_type: state.session.session_type,
  };
  if (sampleMode) {
    payload.decision = verdict;
  } else {
    payload.verdict = verdict;
  }
  const response = await fetch("/api/ratings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    window.alert(`Failed to save rating: ${message}`);
    return;
  }
  document.getElementById("notes").value = "";
  await loadSession();
}

function bindControls() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => submitVerdict(button.dataset.action));
  });
  document.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) {
      return;
    }
    const sampleMode = state.session?.session_type === "sample_review";
    const bindings = sampleMode
      ? { p: "promote", r: "reject", s: "skip" }
      : { a: "A", b: "B", g: "both_good", x: "both_bad", s: "skip" };
    const verdict = bindings[event.key.toLowerCase()];
    if (verdict) {
      event.preventDefault();
      submitVerdict(verdict);
    }
  });
}

bindControls();
loadSession().catch((error) => {
  document.getElementById("promptText").textContent = `Failed to load session: ${error.message}`;
});

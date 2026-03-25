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
  document.getElementById("sessionName").textContent = session.session_name;
  document.getElementById("remainingCount").textContent = `${session.remaining} remaining`;
  document.getElementById("progressValue").textContent = `${session.rated} / ${session.total}`;
  document.getElementById("progressCaption").textContent =
    session.remaining === 0 ? "Review queue complete." : "Use keyboard shortcuts A, B, G, X, or S.";

  const item = state.currentItem;
  if (!item) {
    document.getElementById("caseId").textContent = "All comparisons reviewed";
    document.getElementById("promptText").textContent =
      "The session is complete. Ratings are stored in ratings.jsonl inside the review session folder.";
    document.getElementById("videoGrid").innerHTML = "";
    return;
  }

  document.getElementById("caseId").textContent = item.case_id;
  document.getElementById("promptText").textContent = item.prompt || "Prompt unavailable for this case.";
  const grid = document.getElementById("videoGrid");
  grid.innerHTML = "";
  item.options.forEach((option) => grid.appendChild(buildOptionCard(option)));
}

function buildOptionCard(option) {
  const card = document.createElement("article");
  card.className = "option-card";
  const heading = document.createElement("h3");
  heading.textContent = `Option ${option.slot}`;
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
  const payload = {
    review_id: state.currentItem.review_id,
    verdict,
    confidence: document.getElementById("confidence").value,
    notes: document.getElementById("notes").value,
  };
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
  document.querySelectorAll("[data-verdict]").forEach((button) => {
    button.addEventListener("click", () => submitVerdict(button.dataset.verdict));
  });
  document.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) {
      return;
    }
    const bindings = {
      a: "A",
      b: "B",
      g: "both_good",
      x: "both_bad",
      s: "skip",
    };
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

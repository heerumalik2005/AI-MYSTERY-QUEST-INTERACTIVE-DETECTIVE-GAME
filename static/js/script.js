/* Small fetch helper keeps API calls consistent and handles server errors. */
async function postJSON(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}
function showToast(message, type = "success") {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.dataset.type = type;
  toast.classList.add("visible");
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => toast.classList.remove("visible"), 3200);
}
function updateScore(value) {
  const el = document.getElementById("score-value");
  if (el) el.textContent = value;
}
function updateProgress(value) {
  const bar = document.getElementById("progress-bar");
  const label = document.getElementById("progress-label");
  if (bar) bar.style.width = value + "%";
  if (label) label.textContent = value + "%";
}

/* Evidence is revealed only after the server confirms the examination. */
document.querySelectorAll(".examine-btn").forEach(button => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const data = await postJSON("/api/examine", {clue_id: button.dataset.clue});
      document.getElementById("detail-" + button.dataset.clue).textContent = data.clue.detail;
      document.getElementById("evidence-" + button.dataset.clue).classList.add("is-found");
      button.textContent = "Examined ✓";
      document.getElementById("clue-count").textContent = data.discovered.length + " / " +
        document.querySelectorAll(".evidence-card").length + " FOUND";
      document.getElementById("check-clues").textContent = data.discovered.length + "/" +
        document.querySelectorAll(".evidence-card").length;
      updateProgress(data.progress);
      showToast("Evidence added to your case notes.");
    } catch (error) { button.disabled = false; showToast(error.message, "error"); }
  });
});

/* Puzzle submission awards points only once; server validates the answer. */
document.querySelectorAll(".puzzle-submit").forEach(button => {
  button.addEventListener("click", async () => {
    const id = button.dataset.puzzle;
    const input = document.getElementById("answer-" + id);
    const feedback = document.getElementById("puzzle-feedback-" + id);
    if (!input.value.trim()) { showToast("Enter an answer first.", "error"); return; }
    button.disabled = true;
    try {
      const data = await postJSON("/api/puzzle", {puzzle_id: id, answer: input.value});
      feedback.textContent = data.message;
      feedback.className = "inline-feedback " + (data.correct ? "feedback-good" : "feedback-bad");
      updateScore(data.score);
      updateProgress(data.progress);
      if (data.correct) {
        document.getElementById("check-puzzles").textContent = "1/1";
        button.textContent = "Solved ✓";
      } else button.disabled = false;
    } catch (error) { button.disabled = false; showToast(error.message, "error"); }
  });
});

/* Hint requests are rate-limited by the case's available hint list on the server. */
const hintButton = document.getElementById("hint-btn");
if (hintButton) hintButton.addEventListener("click", async () => {
  hintButton.disabled = true;
  hintButton.textContent = "Thinking...";
  try {
    const data = await postJSON("/api/hint");
    const output = document.getElementById("hint-output");
    const note = document.createElement("p");
    note.textContent = data.hint;
    output.appendChild(note);
    updateScore(data.score);
    hintButton.textContent = data.remaining ? `Another hint −10 pts (${data.remaining})` : "All hints used";
    if (data.remaining) hintButton.disabled = false;
  } catch (error) {
    hintButton.textContent = "Reveal a hint −10 pts";
    hintButton.disabled = false;
    showToast(error.message, "error");
  }
});

/* Chat messages are inserted as text, never as untrusted HTML. */
const chatForm = document.getElementById("chat-form");
if (chatForm) chatForm.addEventListener("submit", async event => {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;
  const windowEl = document.getElementById("chat-window");
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.textContent = question;
  windowEl.appendChild(userMsg);
  input.value = "";
  const pending = document.createElement("div");
  pending.className = "chat-message assistant";
  pending.textContent = "Reviewing the case...";
  windowEl.appendChild(pending);
  windowEl.scrollTop = windowEl.scrollHeight;
  try {
    const data = await postJSON("/api/chat", {question});
    pending.textContent = data.answer;
  } catch (error) { pending.textContent = error.message; }
  windowEl.scrollTop = windowEl.scrollHeight;
});

/* The final answer is checked on the server; the UI reveals the explanation afterwards. */
const accuseButton = document.getElementById("accuse-btn");
if (accuseButton) accuseButton.addEventListener("click", async () => {
  const select = document.getElementById("suspect-choice");
  if (!select.value) { showToast("Select a suspect before submitting.", "error"); return; }
  if (!confirm("Submit your final accusation? You cannot change it afterwards.")) return;
  accuseButton.disabled = true;
  try {
    const data = await postJSON("/api/accuse", {suspect_id: select.value});
    const r = data.result;
    const box = document.getElementById("accusation-result");
    box.hidden = false;
    box.className = "result-box " + (r.correct ? "result-win" : "result-loss");
    box.innerHTML = ""; // Build nodes safely; values are inserted as text.
    const title = document.createElement("h3");
    title.textContent = r.correct ? "Case solved. Excellent work." : "The accusation was incorrect.";
    const details = document.createElement("p");
    details.textContent = `The culprit was ${r.culprit}. Your final score: ${r.score} points.`;
    const solution = document.createElement("p");
    solution.textContent = r.solution;
    const link = document.createElement("a");
    link.href = "/history"; link.className = "text-button"; link.textContent = "View case history →";
    box.append(title, details, solution, link);
    accuseButton.textContent = "Case closed";
    showToast(r.correct ? "Correct accusation! +100 points." : "Incorrect accusation. −20 points.", r.correct ? "success" : "error");
    document.querySelectorAll("button, input, select").forEach(el => { if (el !== link) el.disabled = true; });
  } catch (error) { accuseButton.disabled = false; showToast(error.message, "error"); }
});

/**
 * Technology for Consumer Rights Awareness (CEP)
 * Quiz Controller: Asynchronous Evaluation against Backend Database
 */

document.addEventListener("DOMContentLoaded", () => {
  const quizForm = document.getElementById("quiz-evaluation-form");
  if (!quizForm) return;

  const quizCards = document.querySelectorAll(".quiz-card");
  const radios = document.querySelectorAll(".quiz-radio");
  const progressCount = document.getElementById("progress-count");
  const progressPercentLabel = document.getElementById("progress-percent-label");
  const progressFill = document.getElementById("quiz-progress-fill");
  const submitBtn = document.getElementById("quiz-submit-btn");
  const submitHint = document.getElementById("submit-hint");
  const resultsBanner = document.getElementById("quiz-results-banner");
  const resBadge = document.getElementById("res-badge");
  const resScoreNumber = document.getElementById("res-score-number");
  const resPercentage = document.getElementById("res-percentage");
  const resMessage = document.getElementById("res-message");
  const retakeBtn = document.getElementById("quiz-retake-btn");
  const totalQuestions = quizCards.length;

  // Track answered state
  function updateProgress() {
    const answeredMap = new Set();
    radios.forEach(r => {
      if (r.checked) {
        answeredMap.add(r.getAttribute("data-qid"));
      }
    });

    const count = answeredMap.size;
    if (progressCount) progressCount.textContent = count;
    const pct = totalQuestions ? Math.round((count / totalQuestions) * 100) : 0;
    if (progressPercentLabel) progressPercentLabel.textContent = `${pct}%`;
    if (progressFill) progressFill.style.width = `${pct}%`;

    if (count === totalQuestions) {
      if (submitHint) submitHint.textContent = "All 8 questions answered. Ready to submit!";
      if (submitBtn) {
        submitBtn.classList.remove("btn-subtle");
        submitBtn.classList.add("btn-primary");
      }
    } else {
      if (submitHint) submitHint.textContent = `${count} of ${totalQuestions} answered. You can submit at any time.`;
    }
  }

  // Radio selection highlighting
  radios.forEach(radio => {
    radio.addEventListener("change", () => {
      const qid = radio.getAttribute("data-qid");
      const card = document.getElementById(`quiz-card-${qid}`);
      if (card) {
        card.querySelectorAll(".quiz-option-label").forEach(lbl => {
          lbl.style.borderColor = "var(--border-subtle)";
          lbl.style.backgroundColor = "transparent";
        });
      }
      const label = radio.closest(".quiz-option-label");
      if (label) {
        label.style.borderColor = "var(--teal-700)";
        label.style.backgroundColor = "var(--teal-50)";
      }
      updateProgress();
    });
  });

  // Submit via JSON API
  quizForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Evaluating Answers...";
    }

    const answers = {};
    radios.forEach(r => {
      if (r.checked) {
        answers[r.getAttribute("data-qid")] = r.value;
      }
    });

    try {
      const res = await fetch("/api/quiz/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify({ answers }),
      });

      if (!res.ok) {
        throw new Error("Server returned status " + res.status);
      }

      const data = await res.json();
      displayResults(data);
    } catch (err) {
      console.warn("API evaluation failed, falling back to standard form submission:", err);
      quizForm.submit();
    }
  });

  function displayResults(data) {
    // 1. Reveal results banner
    if (resultsBanner) {
      resultsBanner.style.display = "block";
      resultsBanner.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (resBadge) resBadge.textContent = data.awareness_level;
    if (resScoreNumber) resScoreNumber.textContent = `${data.score} / ${data.total}`;
    if (resPercentage) resPercentage.textContent = `${data.percentage}% Correct`;
    if (resMessage) resMessage.textContent = data.summary_message;

    // 2. Lock inputs and render per-question review
    const resultsMap = {};
    (data.results || []).forEach(item => {
      resultsMap[item.id] = item;
    });

    quizCards.forEach(card => {
      const qid = card.getAttribute("data-qid");
      const item = resultsMap[qid];
      if (!item) return;

      const cardRadios = card.querySelectorAll(".quiz-radio");
      cardRadios.forEach(r => { r.disabled = true; });

      // Highlight options
      const optKeys = ["A", "B", "C", "D"];
      optKeys.forEach(k => {
        const lbl = document.getElementById(`label-${qid}-${k}`);
        if (!lbl) return;

        if (k === item.correct_option) {
          lbl.style.borderColor = "var(--emerald-600)";
          lbl.style.backgroundColor = "var(--emerald-50)";
          const strong = lbl.querySelector("strong");
          if (strong) strong.innerHTML = `✓ ${k}.`;
        } else if (k === item.user_answer && !item.is_correct) {
          lbl.style.borderColor = "var(--crimson-600)";
          lbl.style.backgroundColor = "var(--crimson-50)";
          const strong = lbl.querySelector("strong");
          if (strong) strong.innerHTML = `✗ ${k}.`;
        } else {
          lbl.style.opacity = "0.7";
        }
      });

      // Show explanation box
      const fbBox = document.getElementById(`feedback-${qid}`);
      if (fbBox) {
        fbBox.style.display = "block";
        const heading = fbBox.querySelector(".feedback-heading");
        const expText = fbBox.querySelector(".feedback-explanation");

        if (item.is_correct) {
          fbBox.style.borderLeft = "4px solid var(--emerald-600)";
          fbBox.style.backgroundColor = "var(--emerald-50)";
          if (heading) {
            heading.style.color = "var(--emerald-700)";
            heading.innerHTML = `<span>✓ Correct Answer (${item.correct_option}) &bull; Statutory Grounding</span>`;
          }
        } else {
          fbBox.style.borderLeft = "4px solid var(--crimson-600)";
          fbBox.style.backgroundColor = "var(--crimson-50)";
          if (heading) {
            heading.style.color = "var(--crimson-700)";
            heading.innerHTML = `<span>✗ Incorrect &bull; Correct Answer is <strong>${item.correct_option}</strong></span>`;
          }
        }

        if (expText) {
          expText.innerHTML = `${item.explanation} <br><strong style="color: var(--teal-800); font-size: 0.8125rem;">Statutory Reference: ${item.source_name || 'Consumer Protection Act, 2019'}</strong>`;
        }
      }
    });

    // 3. Hide submit button and show retake
    const submitBar = document.getElementById("quiz-submit-bar");
    if (submitBar) {
      submitBar.innerHTML = `
        <div>
          <span style="font-size: 0.9375rem; color: var(--slate-700); font-weight: 600;">
            Evaluation complete. Your responses are not saved to any database.
          </span>
        </div>
        <div>
          <button type="button" id="quiz-bottom-retake-btn" class="btn btn-secondary">
            Retake Assessment
          </button>
        </div>
      `;
      const bottomRetake = document.getElementById("quiz-bottom-retake-btn");
      if (bottomRetake) bottomRetake.addEventListener("click", () => resetQuiz());
    }
  }

  function resetQuiz() {
    window.location.href = "/quiz";
  }

  if (retakeBtn) {
    retakeBtn.addEventListener("click", () => resetQuiz());
  }

  // Initial calculation
  updateProgress();
});

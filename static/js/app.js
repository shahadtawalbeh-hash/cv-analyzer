const keyForm = document.getElementById("key-form");
const keyMsg = document.getElementById("key-msg");
const cvForm = document.getElementById("cv-form");
const runMsg = document.getElementById("run-msg");
const runBtn = document.getElementById("run-btn");
const cvFileInput = document.getElementById("cv-file-input");
const cvFilenameEl = document.getElementById("cv-filename");
const results = document.getElementById("results");
const resultsLead = document.getElementById("results-lead");
const profileBox = document.getElementById("profile-box");
const matchWrap = document.getElementById("match-wrap");
const trainingWrap = document.getElementById("training-wrap");
const keyPill = document.getElementById("key-pill");
const previewCard = document.getElementById("preview-card");
const extractedPreview = document.getElementById("extracted-preview");
const emailForm = document.getElementById("email-form");
const emailMsg = document.getElementById("email-msg");

const fetchOpts = { credentials: "same-origin" };

function showError(target, text) {
  target.textContent = text;
  target.style.color = "#b91c1c";
}

function showOk(target, text) {
  target.textContent = text;
  target.style.color = "#047857";
}

function updateFilenameHint() {
  if (!cvFileInput || !cvFilenameEl) {
    return;
  }
  if (cvFileInput.files && cvFileInput.files.length) {
    const f = cvFileInput.files[0];
    cvFilenameEl.hidden = false;
    cvFilenameEl.textContent = `Selected: ${f.name}`;
  } else {
    cvFilenameEl.hidden = true;
    cvFilenameEl.textContent = "";
  }
}

async function postKey(event) {
  event.preventDefault();
  const data = new FormData(keyForm);
  keyMsg.textContent = "Wait...";
  keyMsg.style.color = "#4b5563";
  try {
    const res = await fetch("/actions/save-key", {
      method: "POST",
      body: data,
      ...fetchOpts,
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = payload.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join(" ")
        : detail || "Nope";
      throw new Error(msg);
    }
    showOk(keyMsg, payload.message || "Ok.");
    keyPill.textContent = "Key ok";
    keyPill.classList.remove("pill-warn");
    keyPill.classList.add("pill-ok");
    window.location.reload();
  } catch (err) {
    showError(keyMsg, err.message || "Failed");
  }
}

function renderMatches(rows, threshold) {
  matchWrap.innerHTML = "";
  rows.forEach((row, index) => {
    const div = document.createElement("div");
    div.className = "match-row";
    div.style.animationDelay = `${index * 0.05}s`;
    const label = row.ready ? "OK to refer" : "Under bar";
    const cls = row.ready ? "ok" : "low";
    div.innerHTML = `
      <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; align-items:flex-start;">
        <div>
          <strong>${row.title}</strong>
          <div class="match-meta">${row.category} · ${row.company}</div>
        </div>
        <div class="score ${cls}">${row.score}% · ${label}</div>
      </div>
      <p class="match-body">${row.summary}</p>
    `;
    matchWrap.appendChild(div);
  });
  const foot = document.createElement("p");
  foot.className = "match-foot";
  foot.textContent = `Refer bar is ${threshold}%.`;
  matchWrap.appendChild(foot);
}

function renderTraining(items) {
  if (!items.length) {
    trainingWrap.innerHTML =
      "<p class=\"match-meta\">No course links this time.</p>";
    return;
  }
  const list = document.createElement("div");
  items.forEach((item, index) => {
    const row = document.createElement("div");
    row.className = "match-row";
    row.style.animationDelay = `${index * 0.04}s`;
    row.innerHTML = `
      <a href="${item.url}" target="_blank" rel="noreferrer">${item.title}</a>
      <p class="match-body">${item.why}</p>
    `;
    list.appendChild(row);
  });
  trainingWrap.innerHTML = "";
  trainingWrap.appendChild(list);
}

function fillResults(payload, opts) {
  const showDoneMsg = opts && opts.showDoneMsg;
  profileBox.textContent = JSON.stringify(payload.profile || {}, null, 2);
  if (extractedPreview && previewCard) {
    if (payload.extracted_preview) {
      extractedPreview.textContent = payload.extracted_preview;
      previewCard.hidden = false;
    } else {
      previewCard.hidden = true;
    }
  }
  const th = payload.threshold;
  const matches = (payload.matches || []).map((row) => ({
    ...row,
    ready: row.ready !== undefined ? row.ready : row.score >= th,
  }));
  renderMatches(matches, th);
  renderTraining(payload.training || []);
  const anyLow = matches.some((row) => row.score < th);
  resultsLead.textContent = anyLow
    ? "Some jobs under the bar. Courses help."
    : "All jobs at or over the bar on paper.";
  window.__LAST_EMAIL_PAYLOAD__ = payload;
  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
  if (showDoneMsg && payload.text_length != null) {
    showOk(runMsg, `Done. ${payload.text_length} chars from the file.`);
  }
}

let matchRunning = false;

async function runMatchFromForm() {
  if (matchRunning) {
    return;
  }
  if (!window.__HAS_KEY__) {
    showError(runMsg, "Need a key first.");
    return;
  }
  const input = cvForm.querySelector('input[name="cv_file"]');
  if (!input.files || !input.files.length) {
    showError(runMsg, "Pick a PDF.");
    return;
  }
  matchRunning = true;
  runBtn.disabled = true;
  runMsg.textContent = "Working...";
  runMsg.style.color = "#4b5563";
  const body = new FormData();
  body.append("cv_file", input.files[0]);
  try {
    const res = await fetch("/actions/analyze", {
      method: "POST",
      body,
      ...fetchOpts,
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = payload.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join(" ")
        : detail || "Failed";
      throw new Error(msg);
    }
    fillResults(payload, { showDoneMsg: true });
  } catch (err) {
    showError(runMsg, err.message || "Failed");
  } finally {
    matchRunning = false;
    runBtn.disabled = false;
  }
}

function onCvSubmit(event) {
  event.preventDefault();
  runMatchFromForm();
}

function onCvFileChange() {
  updateFilenameHint();
  if (window.__HAS_KEY__ && cvFileInput && cvFileInput.files.length) {
    runMatchFromForm();
  }
}

async function loadRunById(id) {
  runMsg.textContent = "";
  try {
    const res = await fetch(`/api/runs/${id}`, fetchOpts);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.detail || "Could not load");
    }
    payload.run_id = id;
    fillResults(payload, { showDoneMsg: false });
    showOk(runMsg, "Loaded saved run.");
  } catch (err) {
    showError(runMsg, err.message || "Could not load");
  }
}

function buildEmailPlainText(payload) {
  const lines = [];
  const rid = payload.run_id != null ? `#${payload.run_id}` : "";
  lines.push(`CV Fitboard run ${rid}`);
  lines.push(`Pass bar: ${payload.threshold}%`);
  lines.push("");
  lines.push("Profile:");
  lines.push(JSON.stringify(payload.profile || {}, null, 2));
  lines.push("");
  lines.push("Scores:");
  (payload.matches || []).forEach((m) => {
    lines.push(
      `- ${m.title} ${m.score}% ${m.ready ? "(OK to refer)" : "(under bar)"}`,
    );
    lines.push(`  ${m.summary}`);
  });
  lines.push("");
  lines.push("Courses:");
  if ((payload.training || []).length) {
    (payload.training || []).forEach((t) => {
      lines.push(`- ${t.title}`);
      lines.push(`  ${t.url}`);
      lines.push(`  ${t.why}`);
    });
  } else {
    lines.push("(none)");
  }
  if (payload.extracted_preview) {
    lines.push("");
    lines.push("PDF text excerpt:");
    lines.push(payload.extracted_preview);
  }
  return lines.join("\n");
}

async function copyTextSafe(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      return true;
    } catch {
      return false;
    } finally {
      document.body.removeChild(ta);
    }
  }
}

async function onEmailSubmit(event) {
  event.preventDefault();
  if (!emailForm) {
    return;
  }
  const to = (document.getElementById("email-to") || {}).value || "";
  const trimmed = to.trim();
  if (!trimmed || !trimmed.includes("@")) {
    showError(emailMsg, "Type a real email in To.");
    return;
  }
  const payload = window.__LAST_EMAIL_PAYLOAD__;
  if (!payload) {
    showError(emailMsg, "No run loaded. Run a CV first or load a past run.");
    return;
  }
  emailMsg.textContent = "Working...";
  emailMsg.style.color = "#4b5563";

  const full = buildEmailPlainText(payload);
  const copied = await copyTextSafe(full);
  const subject = `CV Fitboard run ${payload.run_id != null ? payload.run_id : ""}`.trim();

  const MAX_MAILTO_BODY = 1200;
  let bodyForMail = full;
  if (bodyForMail.length > MAX_MAILTO_BODY) {
    bodyForMail =
      full.slice(0, MAX_MAILTO_BODY) +
      "\n\n[The rest is in your clipboard. Paste after you hit send.]";
  }

  const mailto = `mailto:${trimmed}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(bodyForMail)}`;
  window.location.href = mailto;

  if (copied) {
    showOk(
      emailMsg,
      "Mail should open. Full report is on your clipboard if you need to paste.",
    );
  } else {
    showOk(emailMsg, "Mail should open. Copy failed, select text from the results and paste.");
  }
}

if (keyForm) {
  keyForm.addEventListener("submit", postKey);
}

if (cvForm) {
  cvForm.addEventListener("submit", onCvSubmit);
}

if (cvFileInput) {
  cvFileInput.addEventListener("change", onCvFileChange);

  const dz = document.getElementById("dropzone");
  if (dz) {
    ["dragenter", "dragover", "dragleave", "drop"].forEach((ev) => {
      dz.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    });
    dz.addEventListener("drop", (e) => {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) {
        return;
      }
      const pdf = Array.from(files).find(
        (f) => f.type === "application/pdf" || /\.pdf$/i.test(f.name),
      );
      if (!pdf) {
        showError(runMsg, "PDF only.");
        return;
      }
      const dt = new DataTransfer();
      dt.items.add(pdf);
      cvFileInput.files = dt.files;
      cvFileInput.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
}

document.querySelectorAll(".load-run").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-id");
    if (id) {
      loadRunById(id);
    }
  });
});

if (emailForm) {
  emailForm.addEventListener("submit", onEmailSubmit);
}

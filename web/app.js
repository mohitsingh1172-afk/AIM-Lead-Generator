// Set this to your deployed Render URL (e.g. "https://aim-lead-generator.onrender.com")
// Leave empty ("") when running locally.
const BACKEND_URL = "https://aim-lead-generator.onrender.com";

const form = document.querySelector("#searchForm");
const button = document.querySelector("#searchButton");
const statusText = document.querySelector("#statusText");
const statusDetail = document.querySelector("#statusDetail");
const progress = document.querySelector("#progress");
const resultsBody = document.querySelector("#resultsBody");
const downloadLink = document.querySelector("#downloadLink");
const businessCount = document.querySelector("#businessCount");
const rowCount = document.querySelector("#rowCount");
const emailCount = document.querySelector("#emailCount");
const queryCount = document.querySelector("#queryCount");
const reminderButton = document.querySelector("#reminderButton");
const reminderDate = document.querySelector("#reminderDate");
const reminderTitle = document.querySelector("#reminderTitle");
const reminderNotes = document.querySelector("#reminderNotes");
const draftPanel = document.querySelector("#draftPanel");
const draftBusiness = document.querySelector("#draftBusiness");
const draftTo = document.querySelector("#draftTo");
const draftSubject = document.querySelector("#draftSubject");
const draftBody = document.querySelector("#draftBody");
const copyDraftButton = document.querySelector("#copyDraftButton");
const closeDraftButton = document.querySelector("#closeDraftButton");
const openMailAppLink = document.querySelector("#openMailAppLink");
const openGmailLink = document.querySelector("#openGmailLink");
const savePanel = document.querySelector("#savePanel");
const savedPath = document.querySelector("#savedPath");
const copySavedPathButton = document.querySelector("#copySavedPathButton");
const keyStatus = document.querySelector("#keyStatus");

let pollTimer = null;
let pollFailures = 0;
let currentRows = [];

async function loadSettings() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/settings`);
    const settings = await response.json();
    if (!response.ok) {
      throw new Error(settings.error || "Could not read saved settings.");
    }
    keyStatus.textContent = settings.hasApiKey
      ? `API key ready from ${settings.apiKeySource}.`
      : "No saved API key yet. Paste one and choose save key.";
  } catch (error) {
    keyStatus.textContent = "Settings unavailable until the local app is running.";
  }
}

function setDefaultReminderDate() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  date.setHours(10, 0, 0, 0);
  reminderDate.value = toLocalInputValue(date);
}

function setStatus(title, detail, value = 0) {
  statusText.textContent = title;
  statusDetail.textContent = detail;
  progress.value = value;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text || "";
  return td;
}

function emailCell(row) {
  const td = document.createElement("td");
  if (!row.email) {
    td.textContent = "No email found";
    td.className = "muted-cell";
    return td;
  }

  const a = document.createElement("a");
  const draft = buildDraft(row);
  a.href = buildMailto(row, draft.subject, draft.body);
  a.textContent = row.email;
  td.append(a);
  return td;
}

function linkCell(url) {
  const td = document.createElement("td");
  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.textContent = "Open";
    td.append(a);
  }
  return td;
}

function actionCell(row) {
  const td = document.createElement("td");
  if (!row.email) {
    td.textContent = "Unavailable";
    td.className = "muted-cell";
    return td;
  }

  const draftButton = document.createElement("button");
  draftButton.className = "table-action";
  draftButton.type = "button";
  draftButton.textContent = "Draft email";
  draftButton.addEventListener("click", () => showDraft(row));
  td.append(draftButton);
  return td;
}

function buildDraft(row) {
  const subject = `Business enquiry for ${row.business_name}`;
  const body = [
    `Hello ${row.business_name},`,
    "",
    "I came across your business and wanted to connect.",
    "",
    "Regards,"
  ].join("\n");
  return { body, subject };
}

function buildMailto(row, subject, body) {
  return `mailto:${encodeURIComponent(row.email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function buildGmailUrl(row, subject, body) {
  const params = new URLSearchParams({
    view: "cm",
    fs: "1",
    to: row.email,
    su: subject,
    body,
  });
  return `https://mail.google.com/mail/?${params.toString()}`;
}

function showDraft(row) {
  const draft = buildDraft(row);
  draftBusiness.textContent = row.business_name || "Email draft";
  draftTo.value = row.email;
  draftSubject.value = draft.subject;
  draftBody.value = draft.body;
  updateDraftLinks(row);
  draftPanel.classList.remove("hidden");
  draftPanel.scrollIntoView({ behavior: "smooth", block: "center" });
}

function currentDraftRow() {
  return {
    business_name: draftBusiness.textContent,
    email: draftTo.value,
  };
}

function updateDraftLinks(row = currentDraftRow()) {
  openMailAppLink.href = buildMailto(row, draftSubject.value, draftBody.value);
  openGmailLink.href = buildGmailUrl(row, draftSubject.value, draftBody.value);
}

function renderRows(rows) {
  resultsBody.replaceChildren();
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 7;
    td.className = "empty";
    td.textContent = "No leads were returned for this search.";
    tr.append(td);
    resultsBody.append(tr);
    return;
  }

  currentRows = rows;
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.append(
      cell(row.business_name),
      emailCell(row),
      actionCell(row),
      cell(row.phone || row.website_phones),
      linkCell(row.website),
      cell(row.rating),
      cell(row.address)
    );
    resultsBody.append(tr);
  }
}

async function pollJob(jobId) {
  const response = await fetch(`${BACKEND_URL}/api/jobs/${jobId}`);
  const job = await response.json();
  if (!response.ok) {
    throw new Error(job.error || "Could not read job status.");
  }

  pollFailures = 0;
  setStatus(job.status === "error" ? "Error" : "Working", job.message || "", job.progress || 0);

  if (job.status === "complete") {
    clearInterval(pollTimer);
    pollTimer = null;
    button.disabled = false;
    button.textContent = "Generate leads";
    setStatus("Complete", job.message || "Lead list ready.", 100);
    renderRows(job.rows || []);
    businessCount.textContent = job.businessCount || 0;
    rowCount.textContent = (job.rows || []).length;
    emailCount.textContent = job.emailCount || 0;
    queryCount.textContent = job.queryCount || 0;
    savedPath.textContent = job.savedPath || "Saved in the exports folder.";
    savePanel.classList.remove("hidden");
    downloadLink.href = job.downloadUrl;
    downloadLink.classList.remove("hidden");
  }

  if (job.status === "error") {
    clearInterval(pollTimer);
    pollTimer = null;
    button.disabled = false;
    button.textContent = "Generate leads";
    renderRows([]);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearInterval(pollTimer);
  downloadLink.classList.add("hidden");
  renderRows([]);
  currentRows = [];
  businessCount.textContent = "0";
  rowCount.textContent = "0";
  emailCount.textContent = "0";
  queryCount.textContent = "0";
  savePanel.classList.add("hidden");
  savedPath.textContent = "No file saved yet.";
  button.disabled = true;
  button.textContent = "Running";
  setStatus("Starting", "Creating search job...", 3);

  const formData = new FormData(form);
  const payload = {
    queries: formData.get("queries"),
    apiKey: formData.get("apiKey"),
    saveApiKey: formData.get("saveApiKey") === "on",
    limit: Number(formData.get("limit")),
    maxPages: Number(formData.get("maxPages")),
    delay: Number(formData.get("delay")),
    respectRobots: formData.get("respectRobots") === "on",
  };

  try {
    const response = await fetch(`${BACKEND_URL}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Search could not start.");
    }
    await loadSettings();
    pollTimer = setInterval(() => pollJob(data.jobId).catch(handlePollingError), 1200);
    await pollJob(data.jobId);
  } catch (error) {
    showError(error);
  }
});

function toLocalInputValue(date) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 16);
}

function toIcsDate(date) {
  return date.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
}

function escapeIcsText(text) {
  return String(text || "")
    .replace(/\\/g, "\\\\")
    .replace(/,/g, "\\,")
    .replace(/;/g, "\\;")
    .replace(/\r?\n/g, "\\n");
}

function downloadTextFile(filename, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function createReminder() {
  if (!reminderDate.value) {
    setStatus("Reminder date needed", "Choose a date and time before creating the calendar file.", progress.value);
    return;
  }

  const start = new Date(reminderDate.value);
  const end = new Date(start.getTime() + 30 * 60000);
  const emailCountValue = currentRows.filter((row) => row.email).length;
  const description = [
    reminderNotes.value,
    "",
    `Generated rows: ${currentRows.length}`,
    `Rows with emails: ${emailCountValue}`,
    "Open the exported CSV from the app to continue outreach."
  ].join("\n");
  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//AIM Lead Generator//Outreach Reminder//EN",
    "BEGIN:VEVENT",
    `UID:${Date.now()}@aim-lead-generator.local`,
    `DTSTAMP:${toIcsDate(new Date())}`,
    `DTSTART:${toIcsDate(start)}`,
    `DTEND:${toIcsDate(end)}`,
    `SUMMARY:${escapeIcsText(reminderTitle.value || "Follow up with generated leads")}`,
    `DESCRIPTION:${escapeIcsText(description)}`,
    "END:VEVENT",
    "END:VCALENDAR"
  ].join("\r\n");

  downloadTextFile("lead-follow-up-reminder.ics", ics, "text/calendar");
  setStatus("Reminder created", "Open the downloaded calendar file to add it to your calendar.", progress.value);
}

reminderButton.addEventListener("click", createReminder);
draftSubject.addEventListener("input", () => updateDraftLinks());
draftBody.addEventListener("input", () => updateDraftLinks());
closeDraftButton.addEventListener("click", () => draftPanel.classList.add("hidden"));
copyDraftButton.addEventListener("click", async () => {
  const text = [`To: ${draftTo.value}`, `Subject: ${draftSubject.value}`, "", draftBody.value].join("\n");
  try {
    await navigator.clipboard.writeText(text);
    setStatus("Draft copied", "Paste it into Gmail, Outlook, or any email app.", progress.value);
  } catch (error) {
    draftBody.select();
    setStatus("Copy manually", "Select the draft text and press Ctrl+C.", progress.value);
  }
});
copySavedPathButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(savedPath.textContent);
    setStatus("Path copied", "The saved CSV path is now copied.", progress.value);
  } catch (error) {
    setStatus("Copy manually", "Select the saved path and press Ctrl+C.", progress.value);
  }
});
setDefaultReminderDate();
loadSettings();

function handlePollingError(error) {
  pollFailures += 1;
  if (pollFailures < 6) {
    setStatus("Working", "Reconnecting to the local app...", progress.value);
    return;
  }
  showError(error);
}

function showError(error) {
  clearInterval(pollTimer);
  pollTimer = null;
  button.disabled = false;
  button.textContent = "Generate leads";
  setStatus("Error", error.message || "Something went wrong.", 100);
}

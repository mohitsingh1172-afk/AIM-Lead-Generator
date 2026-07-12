import csv
import html
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)

JOBS = {}
JOBS_LOCK = threading.Lock()


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Lead Generator</title>
  <style>
    :root {
      --bg: #eef2f5;
      --bg-soft: #f8fafb;
      --panel: #ffffff;
      --panel-2: #fbfcfd;
      --ink: #17212b;
      --muted: #667385;
      --line: #d7dee8;
      --line-strong: #c8d2de;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --accent-soft: #e5f4f1;
      --gold: #b7791f;
      --gold-soft: #fff7e6;
      --bad: #b42318;
      --good: #067647;
      --shadow: 0 14px 32px rgba(23, 33, 43, 0.09);
      --shadow-soft: 0 8px 20px rgba(23, 33, 43, 0.06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, Helvetica, sans-serif;
      color: var(--ink);
      background:
        linear-gradient(180deg, #f8fafb 0, var(--bg) 360px);
    }
    header {
      min-height: 76px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 14px 28px;
      background: #18212a;
      color: #ffffff;
      border-bottom: 1px solid #0f171e;
      box-shadow: 0 8px 20px rgba(15, 23, 30, 0.18);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .brand-mark {
      width: 40px;
      height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      background: var(--accent);
      color: #ffffff;
      font-size: 13px;
      font-weight: 800;
      box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.14);
      flex: 0 0 auto;
    }
    header h1 {
      font-size: 20px;
      margin: 0;
      font-weight: 800;
      letter-spacing: 0;
    }
    .header-subtitle {
      margin-top: 3px;
      color: #b9c6d4;
      font-size: 13px;
      font-weight: 600;
    }
    .header-badge {
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      border-radius: 999px;
      padding: 5px 12px;
      background: rgba(15, 118, 110, 0.2);
      border: 1px solid rgba(148, 210, 203, 0.38);
      color: #dff5f1;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    main {
      display: grid;
      grid-template-columns: 430px minmax(0, 1fr);
      min-height: calc(100vh - 76px);
      gap: 18px;
      padding: 18px;
    }
    aside {
      padding: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      box-shadow: var(--shadow-soft);
      align-self: start;
      overflow: hidden;
    }
    section {
      padding: 0;
      min-width: 0;
    }
    .panel-head {
      padding: 18px 20px 12px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-2);
    }
    .panel-head h2 {
      margin: 0;
      font-size: 16px;
      line-height: 1.25;
    }
    .panel-head p {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    form {
      padding: 4px 20px 20px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 800;
      margin: 16px 0 7px;
      color: #263241;
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      font: inherit;
      background: white;
      color: var(--ink);
      outline: none;
      transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    }
    input:focus, textarea:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14);
    }
    textarea {
      min-height: 120px;
      resize: vertical;
      line-height: 1.4;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    button, a.button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      border: 0;
      border-radius: 8px;
      padding: 0 15px;
      background: var(--accent);
      color: white;
      font-size: 13px;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
      white-space: nowrap;
      box-shadow: 0 8px 16px rgba(15, 118, 110, 0.18);
      transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
    }
    button:hover, a.button:hover {
      background: var(--accent-dark);
      transform: translateY(-1px);
      box-shadow: 0 10px 20px rgba(15, 118, 110, 0.2);
    }
    button:disabled {
      background: #9aa8b8;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
    .secondary {
      background: #f6f8fb;
      color: var(--ink);
      border: 1px solid var(--line);
      box-shadow: none;
    }
    .secondary:hover {
      background: #edf2f7;
      box-shadow: none;
    }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin: 16px 0;
    }
    .results-shell {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .results-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 18px 20px 8px;
      background: var(--panel-2);
      border-bottom: 1px solid var(--line);
    }
    .results-title h2 {
      margin: 0;
      font-size: 17px;
    }
    .results-title p {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 12px;
    }
    .status {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 11px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: white;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }
    .status.running {
      color: var(--accent-dark);
      background: var(--accent-soft);
      border-color: #b8ddd7;
    }
    .status.completed {
      color: var(--good);
      background: #e8f6ef;
      border-color: #b9e5ce;
    }
    .status.failed {
      color: var(--bad);
      background: #fff0ed;
      border-color: #f4c8c1;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 12px;
      padding: 16px 20px 4px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 14px;
      box-shadow: 0 5px 14px rgba(23, 33, 43, 0.04);
      border-top: 3px solid var(--accent);
    }
    .card:nth-child(2) { border-top-color: var(--gold); }
    .card:nth-child(3) { border-top-color: #2563eb; }
    .card:nth-child(4) { border-top-color: var(--good); }
    .card strong {
      display: block;
      font-size: 24px;
      margin-bottom: 4px;
      line-height: 1;
    }
    .card span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .table-wrap {
      overflow: auto;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      background: white;
      max-height: 52vh;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      min-width: 1100px;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      max-width: 280px;
      overflow-wrap: anywhere;
    }
    tbody tr:nth-child(even) td { background: #fbfcfd; }
    tbody tr:hover td { background: var(--accent-soft); }
    th {
      position: sticky;
      top: 0;
      background: #edf3f7;
      z-index: 1;
      font-size: 12px;
      color: #334155;
    }
    pre {
      height: 180px;
      overflow: auto;
      background: #111923;
      color: #dbe8f6;
      border-radius: 10px;
      padding: 12px;
      white-space: pre-wrap;
      font-size: 12px;
      margin: 0 20px 20px;
      border: 1px solid #243244;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-top: 10px;
    }
    .inline-toolbar {
      padding: 0 20px 14px;
      margin: 10px 0 0;
    }
    .log-label {
      margin: 18px 20px 8px;
    }
    code {
      background: #eef3f7;
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 1px 5px;
      color: #324154;
    }
    .message {
      display: none;
      margin-top: 12px;
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 10px 12px;
      font-size: 13px;
      font-weight: 700;
      line-height: 1.4;
    }
    .message.show { display: block; }
    .message.error {
      color: var(--bad);
      background: #fff0ed;
      border-color: #f4c8c1;
    }
    .message.success {
      color: var(--good);
      background: #e8f6ef;
      border-color: #b9e5ce;
    }
    .message.info {
      color: var(--accent-dark);
      background: var(--accent-soft);
      border-color: #b8ddd7;
    }
    @media (max-width: 900px) {
      header {
        align-items: flex-start;
        flex-direction: column;
      }
      main {
        grid-template-columns: 1fr;
        padding: 12px;
      }
      .cards { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
      .results-top { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
<header>
  <div class="brand">
    <span class="brand-mark">LG</span>
    <div>
      <h1>Standard Lead Generator</h1>
      <div class="header-subtitle">Discovery, enrichment, cleaning, and export in one workflow</div>
    </div>
  </div>
  <div class="header-badge">Private local runner</div>
</header>
<main>
  <aside>
    <div class="panel-head">
      <h2>Campaign Setup</h2>
      <p>Enter the market, search terms, limits, and blocked domains before starting a new lead run.</p>
    </div>
    <form id="leadForm">
      <label>Project name</label>
      <input name="projectName" value="lead_project" required />

      <div class="row">
        <div>
          <label>Results per query</label>
          <input name="maxResults" type="number" min="5" max="100" step="5" value="20" />
        </div>
        <div>
          <label>Phone country code</label>
          <input name="phoneCountryCode" value="Auto" />
          <div class="hint" id="phoneCodeHint">Auto detects from each lead location.</div>
        </div>
      </div>

      <label>Scrape.do token</label>
      <input name="scrapedoToken" type="password" placeholder="Optional if set on server" />
      <div class="hint">The token is used for Google discovery and is not saved to config files.</div>

      <label>Locations</label>
      <textarea name="locations" required>United States
United Kingdom</textarea>

      <label>Keywords</label>
      <textarea name="keywords" required>product distributor
product importer
wholesale buyer
private label buyer</textarea>

      <label>Exclude domains</label>
      <textarea name="exclusions">amazon.com
facebook.com
instagram.com
linkedin.com
reddit.com
yelp.com</textarea>

      <div class="toolbar">
        <button type="submit" id="runBtn">Run Pipeline</button>
        <button type="button" id="retryBtn" class="secondary" disabled>Retry Failed</button>
      </div>
      <div id="formMessage" class="message" role="status"></div>
      <div class="hint">Run creates a private job folder under <code>runs/</code>. Large searches can take time.</div>
    </form>
  </aside>

  <section>
    <div class="results-shell">
      <div class="results-top">
        <div class="results-title">
          <h2>Cleaned Results</h2>
          <p>Track progress, inspect leads page by page, and download the cleaned output.</p>
        </div>
        <div class="toolbar">
          <span id="status" class="status">No job</span>
          <a id="downloadXlsx" class="button secondary" href="#" style="display:none">Download Excel</a>
          <a id="downloadCsv" class="button secondary" href="#" style="display:none">Download CSV</a>
        </div>
      </div>

      <div class="cards">
        <div class="card"><strong id="rowsCount">0</strong><span>Rows</span></div>
        <div class="card"><strong id="emailCount">0</strong><span>With Email</span></div>
        <div class="card"><strong id="phoneCount">0</strong><span>With Phone</span></div>
        <div class="card"><strong id="bothCount">0</strong><span>Email + Phone</span></div>
      </div>

      <div class="toolbar inline-toolbar">
        <button id="prevPage" class="secondary" disabled>Previous</button>
        <span id="pageInfo" class="hint">Page 0 of 0</span>
        <button id="nextPage" class="secondary" disabled>Next</button>
      </div>

      <div class="table-wrap">
        <table id="resultsTable">
          <thead></thead>
          <tbody></tbody>
        </table>
      </div>

      <label class="log-label">Job log</label>
      <pre id="logBox"></pre>
    </div>
  </section>
</main>

<script>
let currentJob = null;
let currentPage = 1;
const pageSize = 25;
let pollTimer = null;

function lines(value) {
  return value.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
}

const phoneCodeMap = [
  ['afghanistan', '+93'], ['albania', '+355'], ['algeria', '+213'], ['andorra', '+376'],
  ['angola', '+244'], ['anguilla', '+1'], ['antigua and barbuda', '+1'], ['argentina', '+54'],
  ['armenia', '+374'], ['aruba', '+297'], ['australia', '+61'], ['austria', '+43'],
  ['azerbaijan', '+994'], ['bahamas', '+1'], ['bahrain', '+973'], ['bangladesh', '+880'],
  ['barbados', '+1'], ['belarus', '+375'], ['belgium', '+32'], ['belize', '+501'],
  ['benin', '+229'], ['bermuda', '+1'], ['bhutan', '+975'], ['bolivia', '+591'],
  ['bosnia and herzegovina', '+387'], ['bosnia', '+387'], ['botswana', '+267'], ['brazil', '+55'],
  ['brunei', '+673'], ['bulgaria', '+359'], ['burkina faso', '+226'], ['burundi', '+257'],
  ['cambodia', '+855'], ['cameroon', '+237'], ['canada', '+1'], ['cape verde', '+238'],
  ['cayman islands', '+1'], ['central african republic', '+236'], ['chad', '+235'], ['chile', '+56'],
  ['china', '+86'], ['colombia', '+57'], ['comoros', '+269'], ['congo', '+242'],
  ['costa rica', '+506'], ['croatia', '+385'], ['cuba', '+53'], ['curacao', '+599'],
  ['cyprus', '+357'], ['czech republic', '+420'], ['czechia', '+420'],
  ['democratic republic of the congo', '+243'], ['denmark', '+45'], ['djibouti', '+253'],
  ['dominica', '+1'], ['dominican republic', '+1'], ['ecuador', '+593'], ['egypt', '+20'],
  ['el salvador', '+503'], ['equatorial guinea', '+240'], ['eritrea', '+291'], ['estonia', '+372'],
  ['eswatini', '+268'], ['swaziland', '+268'], ['ethiopia', '+251'], ['fiji', '+679'],
  ['finland', '+358'], ['france', '+33'], ['gabon', '+241'], ['gambia', '+220'],
  ['georgia', '+995'], ['germany', '+49'], ['ghana', '+233'], ['gibraltar', '+350'],
  ['greece', '+30'], ['grenada', '+1'], ['guatemala', '+502'], ['guinea', '+224'],
  ['guinea bissau', '+245'], ['guyana', '+592'], ['haiti', '+509'], ['honduras', '+504'],
  ['hong kong', '+852'], ['hungary', '+36'], ['iceland', '+354'], ['india', '+91'],
  ['indonesia', '+62'], ['iran', '+98'], ['iraq', '+964'], ['ireland', '+353'],
  ['israel', '+972'], ['italy', '+39'], ['ivory coast', '+225'], ['cote d ivoire', '+225'],
  ['jamaica', '+1'], ['japan', '+81'], ['jordan', '+962'], ['kazakhstan', '+7'],
  ['kenya', '+254'], ['kuwait', '+965'], ['kyrgyzstan', '+996'], ['laos', '+856'],
  ['latvia', '+371'], ['lebanon', '+961'], ['lesotho', '+266'], ['liberia', '+231'],
  ['libya', '+218'], ['liechtenstein', '+423'], ['lithuania', '+370'], ['luxembourg', '+352'],
  ['macau', '+853'], ['madagascar', '+261'], ['malawi', '+265'], ['malaysia', '+60'],
  ['maldives', '+960'], ['mali', '+223'], ['malta', '+356'], ['mauritania', '+222'],
  ['mauritius', '+230'], ['mexico', '+52'], ['moldova', '+373'], ['monaco', '+377'],
  ['mongolia', '+976'], ['montenegro', '+382'], ['morocco', '+212'], ['mozambique', '+258'],
  ['myanmar', '+95'], ['burma', '+95'], ['namibia', '+264'], ['nepal', '+977'],
  ['netherlands', '+31'], ['new zealand', '+64'], ['nicaragua', '+505'], ['niger', '+227'],
  ['nigeria', '+234'], ['north macedonia', '+389'], ['norway', '+47'], ['oman', '+968'],
  ['pakistan', '+92'], ['panama', '+507'], ['papua new guinea', '+675'], ['paraguay', '+595'],
  ['peru', '+51'], ['philippines', '+63'], ['poland', '+48'], ['portugal', '+351'],
  ['puerto rico', '+1'], ['qatar', '+974'], ['romania', '+40'], ['russia', '+7'],
  ['rwanda', '+250'], ['saint kitts and nevis', '+1'], ['saint lucia', '+1'],
  ['saint vincent and the grenadines', '+1'], ['samoa', '+685'], ['san marino', '+378'],
  ['saudi arabia', '+966'], ['senegal', '+221'], ['serbia', '+381'], ['seychelles', '+248'],
  ['sierra leone', '+232'], ['singapore', '+65'], ['slovakia', '+421'], ['slovenia', '+386'],
  ['somalia', '+252'], ['south africa', '+27'], ['south korea', '+82'], ['korea', '+82'],
  ['south sudan', '+211'], ['spain', '+34'], ['sri lanka', '+94'], ['sudan', '+249'],
  ['suriname', '+597'], ['sweden', '+46'], ['switzerland', '+41'], ['syria', '+963'],
  ['taiwan', '+886'], ['tajikistan', '+992'], ['tanzania', '+255'], ['thailand', '+66'],
  ['togo', '+228'], ['trinidad and tobago', '+1'], ['tunisia', '+216'], ['turkey', '+90'],
  ['turkmenistan', '+993'], ['uganda', '+256'], ['ukraine', '+380'],
  ['united arab emirates', '+971'], ['uae', '+971'], ['united kingdom', '+44'],
  ['uk', '+44'], ['u.k.', '+44'], ['great britain', '+44'], ['england', '+44'],
  ['scotland', '+44'], ['wales', '+44'], ['northern ireland', '+44'],
  ['united states', '+1'], ['usa', '+1'], ['u.s.a', '+1'], ['u.s.', '+1'],
  ['us', '+1'], ['america', '+1'], ['uruguay', '+598'], ['uzbekistan', '+998'],
  ['venezuela', '+58'], ['vietnam', '+84'], ['viet nam', '+84'], ['yemen', '+967'],
  ['zambia', '+260'], ['zimbabwe', '+263']
];

function detectPhoneCodesFromLocations() {
  const form = document.getElementById('leadForm');
  const locationText = (form.elements.locations.value || '').toLowerCase().replace(/[^a-z0-9\s.]+/g, ' ');
  const found = new Set();
  phoneCodeMap
    .slice()
    .sort((a, b) => b[0].length - a[0].length)
    .forEach(([name, code]) => {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (new RegExp(`(^|\\s)${escaped}($|\\s)`).test(locationText)) {
      found.add(code);
    }
  });
  return Array.from(found);
}

function updatePhoneCodeHint() {
  const input = document.querySelector('[name="phoneCountryCode"]');
  const hint = document.getElementById('phoneCodeHint');
  if (!input || !hint) return;

  const value = input.value.trim().toLowerCase();
  if (value && !['auto', 'automatic'].includes(value)) {
    hint.textContent = `Manual override: all rows will use ${input.value.trim()}.`;
    return;
  }

  const codes = detectPhoneCodesFromLocations();
  if (codes.length) {
    hint.textContent = `Auto mode: rows will use detected phone codes ${codes.join(', ')} based on their location.`;
  } else {
    hint.textContent = 'Auto mode: no country detected yet, so unmatched rows will use +1.';
  }
}

function showFormMessage(message, type = 'info') {
  const box = document.getElementById('formMessage');
  if (!box) return;
  box.className = `message show ${type}`;
  box.textContent = message;
}

function clearFormMessage() {
  const box = document.getElementById('formMessage');
  if (!box) return;
  box.className = 'message';
  box.textContent = '';
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function setStatus(job) {
  const el = document.getElementById('status');
  el.className = 'status ' + (job ? job.status : '');
  el.textContent = job ? `${job.status.toUpperCase()} - ${job.project_name}` : 'No job';
}

async function refreshJob() {
  if (!currentJob) return;
  const data = await api(`/api/jobs/${currentJob}`);
  setStatus(data.job);
  document.getElementById('logBox').textContent = data.job.log_tail || '';
  const done = ['completed', 'failed'].includes(data.job.status);
  document.getElementById('retryBtn').disabled = !done;
  await loadResults(currentPage);
  if (done && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function loadResults(page) {
  if (!currentJob) return;
  const data = await api(`/api/jobs/${currentJob}/results?page=${page}&page_size=${pageSize}`);
  currentPage = data.page;
  document.getElementById('rowsCount').textContent = data.total_rows;
  document.getElementById('emailCount').textContent = data.with_email;
  document.getElementById('phoneCount').textContent = data.with_phone;
  document.getElementById('bothCount').textContent = data.with_both;
  document.getElementById('pageInfo').textContent = `Page ${data.page} of ${data.total_pages}`;
  document.getElementById('prevPage').disabled = data.page <= 1;
  document.getElementById('nextPage').disabled = data.page >= data.total_pages;

  const thead = document.querySelector('#resultsTable thead');
  const tbody = document.querySelector('#resultsTable tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '';
  if (!data.columns.length) return;
  const hr = document.createElement('tr');
  data.columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    hr.appendChild(th);
  });
  thead.appendChild(hr);
  data.rows.forEach(row => {
    const tr = document.createElement('tr');
    data.columns.forEach(col => {
      const td = document.createElement('td');
      td.textContent = row[col] || '';
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  document.getElementById('downloadXlsx').style.display = data.total_rows ? 'inline-flex' : 'none';
  document.getElementById('downloadCsv').style.display = data.total_rows ? 'inline-flex' : 'none';
  document.getElementById('downloadXlsx').href = `/api/jobs/${currentJob}/download.xlsx`;
  document.getElementById('downloadCsv').href = `/api/jobs/${currentJob}/download.csv`;
}

document.getElementById('leadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  document.getElementById('runBtn').disabled = true;
  clearFormMessage();
  try {
    const payload = {
      projectName: form.get('projectName'),
      maxResults: Number(form.get('maxResults') || 20),
      phoneCountryCode: form.get('phoneCountryCode') || 'Auto',
      scrapedoToken: form.get('scrapedoToken') || '',
      locations: lines(form.get('locations') || ''),
      keywords: lines(form.get('keywords') || ''),
      exclusions: lines(form.get('exclusions') || '')
    };
    const data = await api('/api/jobs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    currentJob = data.job_id;
    currentPage = 1;
    showFormMessage('Pipeline started. Progress will appear in the status and job log.', 'success');
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(refreshJob, 2000);
    await refreshJob();
  } catch (err) {
    showFormMessage(err.message, 'error');
  } finally {
    document.getElementById('runBtn').disabled = false;
  }
});

document.getElementById('retryBtn').addEventListener('click', async () => {
  if (!currentJob) return;
  clearFormMessage();
  try {
    await api(`/api/jobs/${currentJob}/retry`, {method: 'POST'});
    showFormMessage('Retry started. Progress will appear in the status and job log.', 'success');
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(refreshJob, 2000);
    await refreshJob();
  } catch (err) {
    showFormMessage(err.message, 'error');
  }
});

document.getElementById('prevPage').addEventListener('click', () => loadResults(currentPage - 1));
document.getElementById('nextPage').addEventListener('click', () => loadResults(currentPage + 1));
document.querySelector('[name="locations"]').addEventListener('input', updatePhoneCodeHint);
document.querySelector('[name="phoneCountryCode"]').addEventListener('input', updatePhoneCodeHint);
updatePhoneCodeHint();
</script>
</body>
</html>"""


def json_response(handler, data, status=HTTPStatus.OK):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def text_response(handler, data, content_type="text/plain; charset=utf-8"):
    payload = data.encode("utf-8")
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def safe_project_name(value):
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("._-") or "lead_project"


def has_scrapedo_token(payload=None, job=None):
    payload = payload or {}
    job = job or {}
    return bool(
        str(payload.get("scrapedoToken") or "").strip()
        or str(job.get("scrapedo_token") or "").strip()
        or os.environ.get("SCRAPEDO_TOKEN", "").strip()
    )


def write_lines(path, lines):
    cleaned = []
    for line in lines:
        line = str(line).strip()
        if line and line not in cleaned:
            cleaned.append(line)
    path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")


def append_log(job, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message.rstrip()}\n"
    with JOBS_LOCK:
        job["log"].append(line)
        job["log"] = job["log"][-400:]
    with open(job["log_file"], "a", encoding="utf-8") as handle:
        handle.write(line)


def set_job_status(job, status):
    with JOBS_LOCK:
        job["status"] = status
        job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def run_command(job, args, env):
    append_log(job, f"$ {' '.join(str(x) for x in args)}")
    process = subprocess.Popen(
        args,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    with JOBS_LOCK:
        job["process_id"] = process.pid
    for line in process.stdout or []:
        append_log(job, line)
    code = process.wait()
    if code:
        raise RuntimeError(f"Command failed with exit code {code}: {' '.join(args)}")


def build_env(job, retry=False):
    env = os.environ.copy()
    token = job.get("scrapedo_token") or env.get("SCRAPEDO_TOKEN", "")
    if token:
        env["SCRAPEDO_TOKEN"] = token
    project = job["project_name"]
    run_dir = Path(job["run_dir"])
    output_dir = run_dir / "outputs"
    config_dir = run_dir / "config"

    env["PROJECT_NAME"] = project
    env["PHONE_COUNTRY_CODE"] = job.get("phone_country_code", "Auto")
    env["ENRICH_INPUT_FILE"] = str(output_dir / f"{project}_for_enrichment.csv")
    env["ENRICH_OUTPUT_FILE"] = str(output_dir / f"{project}_enriched.csv")
    env["CLEAN_INPUT_FILE"] = str(output_dir / f"{project}_enriched.csv")
    env["CLEAN_OUTPUT_FILE"] = str(output_dir / f"{project}_cleaned.csv")
    env["REJECTED_OUTPUT_FILE"] = str(output_dir / f"{project}_rejected.csv")

    if retry:
        env["USE_SCRAPEDO"] = "1"
        env["SCRAPEDO_FIRST"] = "1"
        env["RETRY_FAILED"] = "1"
        env["RETRY_MISSING"] = "1"
        env["RETRY_DNS_FAILED"] = "0"
        env["MAX_PAGES_PER_WEBSITE"] = "2"
        env["REQUEST_DELAY_SECONDS"] = "0.10"
        env["MAX_HTML_BYTES"] = "600000"
        env["DIRECT_CONNECT_TIMEOUT"] = "4"
        env["DIRECT_READ_TIMEOUT"] = "6"
        env["SCRAPEDO_TIMEOUT"] = "12"
        env["STOP_AFTER_CONTACT_FOUND"] = "1"
    else:
        env["LOCATIONS_FILE"] = str(config_dir / "locations.txt")
        env["KEYWORDS_FILE"] = str(config_dir / "keywords.txt")
        env["EXCLUDE_DOMAINS_FILE"] = str(config_dir / "exclude_domains.txt")
        env["DISCOVERY_OUTPUT_FILE"] = str(output_dir / f"{project}_discovered.csv")
        env["MAX_RESULTS_PER_QUERY"] = str(job["max_results"])
        env["SEARCH_START_RESULT"] = "0"
        env["SKIP_COMPLETED_QUERIES"] = "1"
        env["REQUEST_DELAY_SECONDS"] = "2"
        env["GENERIC_DISCOVERY_FILE"] = str(output_dir / f"{project}_discovered.csv")
    return env


def pipeline_thread(job_id, retry=False):
    with JOBS_LOCK:
        job = JOBS[job_id]
    try:
        set_job_status(job, "running")
        env = build_env(job, retry=retry)
        project = job["project_name"]
        output_dir = Path(job["run_dir"]) / "outputs"
        if retry:
            append_log(job, "Starting failed/missing retry")
            run_command(job, [sys.executable, str(SCRIPTS / "enrich.py")], env)
        else:
            if not env.get("SCRAPEDO_TOKEN"):
                raise RuntimeError("SCRAPEDO_TOKEN is required for discovery.")
            append_log(job, "Starting discovery")
            run_command(job, [sys.executable, str(SCRIPTS / "discover.py")], env)
            append_log(job, "Preparing enrichment input")
            env["GENERIC_DISCOVERY_FILE"] = str(output_dir / f"{project}_discovered.csv")
            env["ENRICH_INPUT_FILE"] = str(output_dir / f"{project}_for_enrichment.csv")
            run_command(job, [sys.executable, str(SCRIPTS / "prepare.py")], env)
            append_log(job, "Starting direct enrichment")
            env["USE_SCRAPEDO"] = "0"
            env["SCRAPEDO_FIRST"] = "0"
            env["MAX_PAGES_PER_WEBSITE"] = "3"
            env["REQUEST_DELAY_SECONDS"] = "0.20"
            env["MAX_HTML_BYTES"] = "700000"
            env["DIRECT_CONNECT_TIMEOUT"] = "5"
            env["DIRECT_READ_TIMEOUT"] = "8"
            env["STOP_AFTER_CONTACT_FOUND"] = "1"
            env["RETRY_FAILED"] = "0"
            env["RETRY_MISSING"] = "0"
            run_command(job, [sys.executable, str(SCRIPTS / "enrich.py")], env)

        append_log(job, "Cleaning leads")
        run_command(job, [sys.executable, str(SCRIPTS / "clean.py")], env)
        append_log(job, "Done")
        set_job_status(job, "completed")
    except Exception as exc:
        append_log(job, f"ERROR: {exc}")
        set_job_status(job, "failed")


def create_job(payload):
    project = safe_project_name(payload.get("projectName", "lead_project"))
    job_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS / job_id
    config_dir = run_dir / "config"
    output_dir = run_dir / "outputs"
    config_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    write_lines(config_dir / "locations.txt", payload.get("locations", []))
    write_lines(config_dir / "keywords.txt", payload.get("keywords", []))
    write_lines(config_dir / "exclude_domains.txt", payload.get("exclusions", []))

    job = {
        "id": job_id,
        "project_name": project,
        "status": "queued",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "max_results": int(payload.get("maxResults") or 20),
        "phone_country_code": str(payload.get("phoneCountryCode") or "Auto"),
        "scrapedo_token": str(payload.get("scrapedoToken") or ""),
        "log": [],
        "log_file": str(run_dir / "job.log"),
        "process_id": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    thread = threading.Thread(target=pipeline_thread, args=(job_id,), daemon=True)
    thread.start()
    return job_id


def public_job(job):
    return {
        "id": job["id"],
        "project_name": job["project_name"],
        "status": job["status"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "run_dir": job["run_dir"],
        "process_id": job["process_id"],
        "log_tail": "".join(job["log"][-120:]),
    }


def cleaned_path(job):
    return Path(job["run_dir"]) / "outputs" / f"{job['project_name']}_cleaned.csv"


def rejected_path(job):
    return Path(job["run_dir"]) / "outputs" / f"{job['project_name']}_rejected.csv"


def read_cleaned_rows(job):
    path = cleaned_path(job)
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def xlsx_col_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def sheet_xml(columns, rows):
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    all_rows = [columns] + [[row.get(col, "") for col in columns] for row in rows]
    for r_idx, values in enumerate(all_rows, start=1):
        parts.append(f'<row r="{r_idx}">')
        for c_idx, value in enumerate(values, start=1):
            ref = f"{xlsx_col_name(c_idx)}{r_idx}"
            safe = html.escape(str(value or ""), quote=False)
            parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{safe}</t></is></c>')
        parts.append("</row>")
    parts.extend(["</sheetData>", "</worksheet>"])
    return "".join(parts)


def build_xlsx(columns, rows, target):
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        zf.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Cleaned Leads" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml(columns, rows))


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                text_response(self, INDEX_HTML, "text/html; charset=utf-8")
                return
            if path == "/api/jobs":
                with JOBS_LOCK:
                    jobs = [public_job(job) for job in JOBS.values()]
                json_response(self, {"jobs": jobs})
                return
            match = re.match(r"^/api/jobs/([^/]+)$", path)
            if match:
                job = self.get_job(match.group(1))
                json_response(self, {"job": public_job(job)})
                return
            match = re.match(r"^/api/jobs/([^/]+)/results$", path)
            if match:
                job = self.get_job(match.group(1))
                query = parse_qs(parsed.query)
                page = max(1, int(query.get("page", ["1"])[0]))
                page_size = max(1, min(100, int(query.get("page_size", ["25"])[0])))
                columns, rows = read_cleaned_rows(job)
                total = len(rows)
                total_pages = max(1, (total + page_size - 1) // page_size)
                page = min(page, total_pages)
                start = (page - 1) * page_size
                chunk = rows[start : start + page_size]
                json_response(
                    self,
                    {
                        "columns": columns,
                        "rows": chunk,
                        "page": page,
                        "page_size": page_size,
                        "total_rows": total,
                        "total_pages": total_pages,
                        "with_email": sum(bool(row.get("Emails", "").strip()) for row in rows),
                        "with_phone": sum(bool(row.get("Phones", "").strip()) for row in rows),
                        "with_both": sum(
                            bool(row.get("Emails", "").strip())
                            and bool(row.get("Phones", "").strip())
                            for row in rows
                        ),
                    },
                )
                return
            match = re.match(r"^/api/jobs/([^/]+)/download\.csv$", path)
            if match:
                self.download_file(self.get_job(match.group(1)), "csv")
                return
            match = re.match(r"^/api/jobs/([^/]+)/download\.xlsx$", path)
            if match:
                self.download_file(self.get_job(match.group(1)), "xlsx")
                return
            json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/jobs":
                payload = self.read_json()
                if not has_scrapedo_token(payload=payload):
                    json_response(
                        self,
                        {
                            "error": (
                                "Scrape.do token is missing. Paste it in the Scrape.do token field, "
                                "or start the server from PowerShell after setting SCRAPEDO_TOKEN."
                            )
                        },
                        HTTPStatus.BAD_REQUEST,
                    )
                    return
                job_id = create_job(payload)
                json_response(self, {"job_id": job_id}, HTTPStatus.CREATED)
                return
            match = re.match(r"^/api/jobs/([^/]+)/retry$", parsed.path)
            if match:
                job = self.get_job(match.group(1))
                if job["status"] == "running":
                    json_response(self, {"error": "Job is already running"}, HTTPStatus.CONFLICT)
                    return
                if not has_scrapedo_token(job=job):
                    json_response(
                        self,
                        {
                            "error": (
                                "Scrape.do token is missing. Start a new run with the token pasted in, "
                                "or restart the server after setting SCRAPEDO_TOKEN."
                            )
                        },
                        HTTPStatus.BAD_REQUEST,
                    )
                    return
                thread = threading.Thread(
                    target=pipeline_thread, args=(job["id"], True), daemon=True
                )
                thread.start()
                json_response(self, {"job_id": job["id"], "status": "queued"})
                return
            json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            json_response(self, {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def get_job(self, job_id):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
        if not job:
            raise ValueError("Unknown job")
        return job

    def download_file(self, job, kind):
        columns, rows = read_cleaned_rows(job)
        if not rows:
            json_response(self, {"error": "No cleaned results yet"}, HTTPStatus.NOT_FOUND)
            return
        if kind == "csv":
            path = cleaned_path(job)
            data = path.read_bytes()
            filename = f"{job['project_name']}_cleaned.csv"
            content_type = "text/csv"
        else:
            path = Path(job["run_dir"]) / "outputs" / f"{job['project_name']}_cleaned.xlsx"
            build_xlsx(columns, rows, path)
            data = path.read_bytes()
            filename = f"{job['project_name']}_cleaned.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


def main():
    port = int(os.getenv("LEAD_APP_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"Lead Generator running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

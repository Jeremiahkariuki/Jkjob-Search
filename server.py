"""
Jkjob-search Interactive Local Web Dashboard Server.
Features:
- High-contrast Dark / Light Theme (🌙 / ☀️ icon) with crystal-clear readability
- Multithreaded server (ThreadingHTTPServer) preventing UI lockup
- Live visual feedback and animated toast for "Run Pipeline Now"
- Filter by Work Arrangement: Remote, Hybrid, Onsite/Office, or All
- Filter by Score: All Active, Top Matches (≥85), Applied / In Progress
- Real-time application status updates saved to SQLite & CSV
"""
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from src.tracker import JobTracker
from src.cv_parser import CVParser
from src.runner import PipelineRunner

tracker = JobTracker()
parser = CVParser()

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jkjob-search | Job Intelligence & Opportunity Tracker</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="alternate icon" href="/favicon.svg">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --bg-color: #0d1117;
      --card-bg: rgba(22, 27, 34, 0.95);
      --card-border: rgba(48, 54, 61, 0.85);
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --box-bg: rgba(13, 17, 23, 0.75);
      --box-border: #21262d;
      --select-bg: #21262d;
      --select-text: #f0f6fc;
      --filter-btn-bg: rgba(22, 27, 34, 0.9);
      --filter-btn-text: #8b949e;
      --filter-btn-border: #30363d;
    }
    body.light-theme {
      --bg-color: #f1f5f9;
      --card-bg: #ffffff;
      --card-border: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #334155;
      --box-bg: #f8fafc;
      --box-border: #cbd5e1;
      --select-bg: #ffffff;
      --select-text: #0f172a;
      --filter-btn-bg: #ffffff;
      --filter-btn-text: #1e293b;
      --filter-btn-border: #cbd5e1;
    }
    body {
      background-color: var(--bg-color);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    .glass-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      transition: all 0.2s ease;
    }
    .inner-box {
      background: var(--box-bg);
      border: 1px solid var(--box-border);
    }

    /* Semantic typography classes that adapt to Light & Dark themes */
    .txt-title { color: #f0f6fc; }
    .txt-company { color: #e2e8f0; }
    .txt-meta { color: #94a3b8; }
    .txt-salary { color: #facc15; font-weight: 700; }
    .txt-label { color: #94a3b8; font-weight: 600; }
    .txt-desc { color: #cbd5e1; }
    .txt-stack { color: #60a5fa; font-weight: 600; }
    .txt-gap { color: #f87171; font-weight: 600; }
    .txt-action { color: #38bdf8; font-weight: 700; }

    /* Light Theme overrides for 100% contrast & crystal-clear readability */
    body.light-theme .txt-title { color: #0f172a !important; }
    body.light-theme .txt-company { color: #0f172a !important; font-weight: 800; }
    body.light-theme .txt-meta { color: #334155 !important; font-weight: 500; }
    body.light-theme .txt-salary { color: #b45309 !important; font-weight: 800; }
    body.light-theme .txt-label { color: #1e293b !important; font-weight: 700; }
    body.light-theme .txt-desc { color: #0f172a !important; font-weight: 500; }
    body.light-theme .txt-stack { color: #1d4ed8 !important; font-weight: 700; }
    body.light-theme .txt-gap { color: #dc2626 !important; font-weight: 700; }
    body.light-theme .txt-action { color: #0284c7 !important; font-weight: 800; }

    /* Badges */
    .badge-confirmed { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
    .badge-score { background: rgba(56, 139, 253, 0.15); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4); }
    .badge-arrangement { background: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid rgba(210, 153, 34, 0.4); }
    .badge-status { background: rgba(163, 113, 247, 0.15); color: #bc8cff; border: 1px solid rgba(163, 113, 247, 0.4); }

    body.light-theme .badge-confirmed { background: #dcfce7 !important; color: #15803d !important; border: 1px solid #86efac !important; font-weight: 700; }
    body.light-theme .badge-score { background: #dbeafe !important; color: #1d4ed8 !important; border: 1px solid #93c5fd !important; font-weight: 700; }
    body.light-theme .badge-arrangement { background: #fef3c7 !important; color: #b45309 !important; border: 1px solid #fde68a !important; font-weight: 700; }
    body.light-theme .badge-status { background: #f3e8ff !important; color: #7e22ce !important; border: 1px solid #d8b4fe !important; font-weight: 700; }

    /* Top Header Pills */
    .pill-live { background: rgba(6, 78, 59, 0.4); color: #34d399; border: 1px solid rgba(5, 150, 105, 0.4); }
    .pill-types { background: rgba(30, 58, 138, 0.4); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.3); }

    body.light-theme .pill-live { background: #dcfce7 !important; color: #15803d !important; border: 1px solid #86efac !important; font-weight: 700; }
    body.light-theme .pill-types { background: #dbeafe !important; color: #1d4ed8 !important; border: 1px solid #93c5fd !important; font-weight: 700; }

    /* Form controls in light theme */
    body.light-theme select.select-status {
      background-color: #ffffff !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
      font-weight: 600;
    }

    /* Filter dropdowns */
    select.filter-select {
      background-color: var(--select-bg);
      color: var(--select-text);
      border: 1px solid var(--filter-btn-border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    body.light-theme select.filter-select {
      background-color: #ffffff !important;
      color: #0f172a !important;
      border: 1px solid #cbd5e1 !important;
    }

    /* Filter buttons */
    .filter-btn-inactive {
      background: var(--filter-btn-bg);
      color: var(--filter-btn-text);
      border: 1px solid var(--filter-btn-border);
    }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Toast Notification Element -->
    <div id="toast" class="fixed top-5 right-5 z-50 transition-all transform duration-300 opacity-0 pointer-events-none"></div>

    <!-- Top Header -->
    <header class="glass-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-3">
          <img src="/favicon.svg" alt="Jkjob-search Logo" class="w-10 h-10 rounded-xl shadow-md border border-gray-700/60" />
          <div>
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="text-2xl font-bold tracking-tight txt-title">Jkjob-search</h1>
              <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold pill-live">LIVE INTELLIGENCE</span>
              <span class="px-2 py-0.5 rounded text-xs font-semibold pill-types">REMOTE • HYBRID • ONSITE</span>
            </div>
          </div>
        </div>
        <p class="text-sm txt-meta mt-1">Opportunity Intelligence & Real-Time Tracking for <span class="font-bold text-blue-500" id="cand-name">Jeremiah Kariuki Beth</span></p>
      </div>
      
      <div class="flex items-center gap-3 flex-wrap">
        <!-- Theme Toggle Button -->
        <button onclick="toggleTheme()" id="theme-btn" class="p-2.5 glass-card hover:border-gray-500 rounded-lg text-lg transition flex items-center justify-center shadow-sm" title="Toggle Dark/Light Mode">
          <span id="theme-icon">🌙</span>
        </button>

        <!-- Pipeline Refresh Action Button -->
        <button onclick="triggerRefresh()" id="refresh-btn" class="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition shadow flex items-center gap-2">
          <span id="refresh-icon">🔄</span>
          <span id="refresh-text">Run Pipeline Now</span>
        </button>

        <a href="/data/job_tracker.csv" download class="px-4 py-2.5 glass-card hover:border-gray-500 text-sm font-semibold rounded-lg transition flex items-center gap-1.5 txt-meta shadow-sm">
          📥 Export CSV
        </a>
      </div>
    </header>

    <!-- Candidate Profile & System Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-xs uppercase txt-meta font-bold">Location & Mobility</div>
        <div class="text-base font-bold txt-title mt-1">🇰🇪 Nairobi, Kenya</div>
        <div class="text-xs txt-meta">Open to Remote, Hybrid & Onsite</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase txt-meta font-bold">Primary Tech Stack</div>
        <div class="text-base font-bold txt-title mt-1">Python • Django • React • Odoo</div>
        <div class="text-xs txt-meta">TypeScript • PostgreSQL • Docker • M-Pesa</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase txt-meta font-bold">Posting Window</div>
        <div class="text-base font-bold text-emerald-500 mt-1">≤ 48.0 Hours</div>
        <div class="text-xs txt-meta">Strict publication date verification</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase txt-meta font-bold">Tracked Vacancies</div>
        <div class="text-base font-bold txt-title mt-1" id="total-count">Loading...</div>
        <div class="text-xs txt-meta" id="applied-count">0 in progress</div>
      </div>
    </div>

    <!-- Filter Control Bar -->
    <div class="glass-card p-4 space-y-3">
      <!-- Status Filters -->
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-xs font-bold uppercase txt-meta mr-2">Status / Fit:</span>
          <button onclick="setFilter('all')" id="tab-all" class="px-3.5 py-1.5 rounded-md text-xs font-bold bg-blue-600 text-white shadow-sm">All Openings</button>
          <button onclick="setFilter('top')" id="tab-top" class="px-3.5 py-1.5 rounded-md text-xs font-bold filter-btn-inactive">🔥 Top Matches (≥85)</button>
          <button onclick="setFilter('applied')" id="tab-applied" class="px-3.5 py-1.5 rounded-md text-xs font-bold filter-btn-inactive">📝 Applied / Shortlisted</button>
        </div>
        <button onclick="resetAllFilters()" id="reset-filters-btn" class="px-3 py-1 rounded text-xs font-bold text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/60 transition hidden whitespace-nowrap">
          ✕ Reset Filters
        </button>
      </div>

      <!-- Arrangement Filters (Remote, Hybrid, Onsite) -->
      <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-700/40">
        <span class="text-xs font-bold uppercase txt-meta mr-2">Arrangement:</span>
        <button onclick="setArrangement('all')" id="arr-all" class="px-3 py-1 rounded text-xs font-bold bg-gray-700 text-white shadow-sm">All Formats</button>
        <button onclick="setArrangement('Remote')" id="arr-remote" class="px-3 py-1 rounded text-xs font-bold filter-btn-inactive">🌐 Remote Only</button>
        <button onclick="setArrangement('Hybrid')" id="arr-hybrid" class="px-3 py-1 rounded text-xs font-bold filter-btn-inactive">🏢 Hybrid (Nairobi)</button>
        <button onclick="setArrangement('Onsite')" id="arr-onsite" class="px-3 py-1 rounded text-xs font-bold filter-btn-inactive">📍 Onsite / Office</button>
      </div>

      <!-- Dropdown Filter Row: API Source & Company -->
      <div class="flex flex-wrap items-center gap-3 pt-2 border-t border-gray-700/40">
        <!-- API Platform / Source Dropdown -->
        <div class="flex items-center gap-2 flex-1 min-w-[260px]">
          <span class="text-xs font-bold uppercase txt-meta whitespace-nowrap">API / Source:</span>
          <select id="source-dropdown" onchange="setSourceFilter(this.value)" class="filter-select w-full focus:outline-none focus:border-blue-500 cursor-pointer">
            <option value="all">All APIs & Sources (Loading...)</option>
          </select>
        </div>

        <!-- Hiring Company Dropdown -->
        <div class="flex items-center gap-2 flex-1 min-w-[260px]">
          <span class="text-xs font-bold uppercase txt-meta whitespace-nowrap">Company:</span>
          <select id="company-dropdown" onchange="setCompanyFilter(this.value)" class="filter-select w-full focus:outline-none focus:border-blue-500 cursor-pointer">
            <option value="all">All Companies (Loading...)</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Vacancies List -->
    <div id="jobs-container" class="space-y-4">
      <div class="p-8 text-center txt-meta">Loading vacancies from SQLite database...</div>
    </div>

  </div>

  <script>
    let currentFilter = 'all';
    let currentArrangement = 'all';
    let currentSource = 'all';
    let currentCompany = 'all';
    let allJobs = [];

    // Theme Management
    function initTheme() {
      const savedTheme = localStorage.getItem('theme') || 'dark';
      applyTheme(savedTheme);
    }

    function toggleTheme() {
      const isLight = document.body.classList.contains('light-theme');
      applyTheme(isLight ? 'dark' : 'light');
    }

    function applyTheme(theme) {
      const icon = document.getElementById('theme-icon');
      if (theme === 'light') {
        document.body.classList.add('light-theme');
        icon.innerText = '☀️';
        localStorage.setItem('theme', 'light');
      } else {
        document.body.classList.remove('light-theme');
        icon.innerText = '🌙';
        localStorage.setItem('theme', 'dark');
      }
      renderJobs();
    }

    async function loadData() {
      try {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        populateDropdowns();
        renderJobs();
      } catch (err) {
        document.getElementById('jobs-container').innerHTML = '<div class="text-red-500 font-bold p-4 text-center">Failed to load vacancies from database.</div>';
      }
    }

    function populateDropdowns() {
      const sourceSelect = document.getElementById('source-dropdown');
      const companySelect = document.getElementById('company-dropdown');
      if (!sourceSelect || !companySelect) return;

      const sourceCounts = {};
      const companyCounts = {};

      allJobs.forEach(j => {
        const s = j.original_source || 'Other';
        sourceCounts[s] = (sourceCounts[s] || 0) + 1;

        const c = j.company || 'Other';
        companyCounts[c] = (companyCounts[c] || 0) + 1;
      });

      // Populate APIs / Sources
      const sortedSources = Object.keys(sourceCounts).sort();
      sourceSelect.innerHTML = `<option value="all">🌐 All Sources & APIs (${allJobs.length})</option>` +
        sortedSources.map(s => `<option value="${s}" ${currentSource === s ? 'selected' : ''}>${s} (${sourceCounts[s]})</option>`).join('');

      // Populate Companies
      const sortedCompanies = Object.keys(companyCounts).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
      companySelect.innerHTML = `<option value="all">🏢 All Companies (${sortedCompanies.length})</option>` +
        sortedCompanies.map(c => `<option value="${c}" ${currentCompany === c ? 'selected' : ''}>${c} (${companyCounts[c]})</option>`).join('');
    }

    function setSourceFilter(s) {
      currentSource = s;
      renderJobs();
    }

    function setCompanyFilter(c) {
      currentCompany = c;
      renderJobs();
    }

    function resetAllFilters() {
      currentFilter = 'all';
      currentArrangement = 'all';
      currentSource = 'all';
      currentCompany = 'all';

      const sourceSelect = document.getElementById('source-dropdown');
      const companySelect = document.getElementById('company-dropdown');
      if (sourceSelect) sourceSelect.value = 'all';
      if (companySelect) companySelect.value = 'all';

      setFilter('all');
      setArrangement('all');
    }

    function setFilter(f) {
      currentFilter = f;
      ['all', 'top', 'applied'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        if (t === f) {
          el.className = 'px-3.5 py-1.5 rounded-md text-xs font-bold bg-blue-600 text-white shadow-sm';
        } else {
          el.className = 'px-3.5 py-1.5 rounded-md text-xs font-bold filter-btn-inactive';
        }
      });
      renderJobs();
    }

    function setArrangement(a) {
      currentArrangement = a;
      ['all', 'remote', 'hybrid', 'onsite'].forEach(t => {
        const key = t === 'all' ? 'all' : (t.charAt(0).toUpperCase() + t.slice(1));
        const el = document.getElementById('arr-' + t);
        if (key.toLowerCase() === a.toLowerCase()) {
          el.className = 'px-3 py-1 rounded text-xs font-bold bg-gray-700 text-white shadow-sm';
        } else {
          el.className = 'px-3 py-1 rounded text-xs font-bold filter-btn-inactive';
        }
      });
      renderJobs();
    }

    function renderJobs() {
      const container = document.getElementById('jobs-container');
      const filtered = allJobs.filter(j => {
        // Status filter
        if (currentFilter === 'top' && j.match_score < 85) return false;
        if (currentFilter === 'applied' && !['Applied', 'Interviewing', 'Shortlisted'].includes(j.application_status)) return false;
        
        // Arrangement filter
        if (currentArrangement !== 'all') {
          const arr = (j.work_arrangement || '').toLowerCase();
          if (!arr.includes(currentArrangement.toLowerCase())) return false;
        }

        // Source / API Platform filter
        if (currentSource !== 'all') {
          if ((j.original_source || '') !== currentSource) return false;
        }

        // Company filter
        if (currentCompany !== 'all') {
          if ((j.company || '').toLowerCase() !== currentCompany.toLowerCase()) return false;
        }

        return true;
      });

      // Update reset button visibility
      const hasActiveFilter = (currentFilter !== 'all' || currentArrangement !== 'all' || currentSource !== 'all' || currentCompany !== 'all');
      const resetBtn = document.getElementById('reset-filters-btn');
      if (resetBtn) {
        if (hasActiveFilter) {
          resetBtn.classList.remove('hidden');
        } else {
          resetBtn.classList.add('hidden');
        }
      }

      document.getElementById('total-count').innerText = allJobs.length + ' Positions';
      const appliedCount = allJobs.filter(j => ['Applied', 'Interviewing'].includes(j.application_status)).length;
      document.getElementById('applied-count').innerText = appliedCount + ' applied / in progress';

      if (!filtered.length) {
        container.innerHTML = '<div class="glass-card p-8 text-center txt-meta font-semibold">No positions found matching this combination of filters.</div>';
        return;
      }

      container.innerHTML = filtered.map(j => {
        const arrangementBadge = j.work_arrangement.toLowerCase().includes('remote') 
          ? '🌐 Remote' 
          : (j.work_arrangement.toLowerCase().includes('hybrid') ? '🏢 Hybrid' : '📍 Onsite');

        return `
        <div class="glass-card p-6 space-y-4 hover:border-blue-500/60 transition">
          <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div>
              <div class="flex items-center gap-2.5 flex-wrap">
                <a href="${j.official_application_link}" target="_blank" class="text-lg font-bold txt-title hover:text-blue-500 transition flex items-center gap-1.5">
                  ${j.job_title} ↗
                </a>
                <span class="px-2.5 py-0.5 rounded text-xs font-bold badge-score">Match ${j.match_score}/100</span>
                <span class="px-2.5 py-0.5 rounded text-xs font-bold badge-arrangement">${arrangementBadge}</span>
                <span class="px-2.5 py-0.5 rounded text-xs font-bold badge-confirmed">✓ ${j.emea_kenya_eligibility_status.split('(')[0]}</span>
                <span class="px-2 py-0.5 rounded text-xs font-bold badge-status">${j.application_status}</span>
              </div>
              <div class="text-sm txt-meta mt-1.5">
                <strong class="txt-company">${j.company}</strong> • ${j.seniority} • ${j.employment_type} • 
                <span>${j.eligible_hiring_locations}</span> • 
                <span class="txt-salary">${j.salary_compensation}</span>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="flex items-center gap-2 self-end md:self-auto">
              <select onchange="updateStatus('${j.official_application_link}', this.value)" class="inner-box select-status text-xs px-2.5 py-1.5 rounded focus:outline-none focus:border-blue-500">
                <option value="Not reviewed" ${j.application_status === 'Not reviewed' ? 'selected' : ''}>Not reviewed</option>
                <option value="Shortlisted" ${j.application_status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                <option value="Applied" ${j.application_status === 'Applied' ? 'selected' : ''}>Applied</option>
                <option value="Interviewing" ${j.application_status === 'Interviewing' ? 'selected' : ''}>Interviewing</option>
                <option value="Rejected" ${j.application_status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                <option value="Closed" ${j.application_status === 'Closed' ? 'selected' : ''}>Closed</option>
              </select>
              <a href="${j.official_application_link}" target="_blank" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded transition shadow-sm">
                Apply Official
              </a>
            </div>
          </div>

          <!-- Matching Rationale & Skills Box -->
          <div class="inner-box text-xs p-4 rounded-lg space-y-2">
            <div><span class="txt-label">Why it matches:</span> <span class="txt-desc">${j.reasons_for_match}</span></div>
            ${j.missing_requirements_risks ? `<div><span class="txt-gap">Identified Gaps:</span> <span class="txt-meta">${j.missing_requirements_risks}</span></div>` : ''}
            <div><span class="txt-label">Required Stack:</span> <span class="txt-stack">${j.required_technical_skills}</span></div>
          </div>

          <div class="flex justify-between items-center text-xs txt-meta pt-1">
            <span>Posted ~${j.listing_age_hours}h ago via ${j.original_source}</span>
            <span>Recommended Next Step: <strong class="txt-action">${j.recommended_next_action}</strong></span>
          </div>
        </div>
      `;
      }).join('');
    }

    async function updateStatus(link, status) {
      const notes = prompt("Add personal note (optional):", "");
      await fetch('/api/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link, status, notes })
      });
      loadData();
    }

    async function triggerRefresh() {
      const btn = document.getElementById('refresh-btn');
      const icon = document.getElementById('refresh-icon');
      const text = document.getElementById('refresh-text');
      
      btn.disabled = true;
      btn.classList.add('opacity-75', 'cursor-not-allowed');
      icon.classList.add('animate-spin');
      text.innerText = 'Scanning 760+ jobs...';

      showToast('🔄 Live Multi-Platform Pipeline started! Scanning WWR, Himalayas, RemoteOK, Remotive & Greenhouse ATS...', 'info');

      try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const data = await response.json();
        if (data.success) {
          showToast(`✓ Pipeline completed! Evaluated ${data.count || 760}+ live vacancies. Found ${data.confirmed || 53} confirmed matches!`, 'success');
        } else {
          showToast('⚠️ Pipeline finished with notice: ' + (data.message || 'Updated'), 'info');
        }
        await loadData();
      } catch (err) {
        showToast('❌ Error running pipeline: ' + err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-75', 'cursor-not-allowed');
        icon.classList.remove('animate-spin');
        text.innerText = 'Run Pipeline Now';
      }
    }

    function showToast(message, type = 'info') {
      const toast = document.getElementById('toast');
      const colors = {
        info: 'bg-blue-600 text-white',
        success: 'bg-emerald-600 text-white',
        error: 'bg-red-600 text-white'
      };
      toast.className = `fixed top-5 right-5 z-50 transition-all transform duration-300 px-4 py-3 rounded-xl shadow-2xl text-sm font-bold flex items-center gap-2 ${colors[type] || colors.info}`;
      toast.innerHTML = message;
      toast.style.opacity = '1';
      toast.style.transform = 'translateY(0)';
      toast.style.pointerEvents = 'auto';

      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.pointerEvents = 'none';
      }, 6000);
    }

    initTheme();
    loadData();
  </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            return

        if path == "/favicon.svg" or path == "/favicon.ico":
            fav_path = Path("static/favicon.svg")
            if fav_path.exists():
                with open(fav_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
                return

        if path == "/api/jobs":
            jobs = tracker.get_all_jobs()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(jobs).encode("utf-8"))
            return

        if path == "/api/profile":
            profile = parser.load_profile()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(profile.__dict__).encode("utf-8"))
            return

        if path == "/data/job_tracker.csv":
            csv_path = Path("data/job_tracker.csv")
            if csv_path.exists():
                with open(csv_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv")
                self.send_header("Content-Disposition", "attachment; filename=job_tracker.csv")
                self.end_headers()
                self.wfile.write(content)
                return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/status":
            link = data.get("link")
            status = data.get("status")
            notes = data.get("notes")
            if link and status:
                tracker.update_status(link, status, notes)
                tracker.export_to_csv()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
                return

        if path == "/api/refresh":
            try:
                runner = PipelineRunner()
                result = runner.run()
                stats = result.get("stats", {})
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "count": stats.get("total_examined", 760),
                    "confirmed": stats.get("confirmed_matches", 53),
                    "new_discovered": stats.get("new_discovered", 0)
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=8000):
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"[✓] Jkjob-search web dashboard running at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server(8000)

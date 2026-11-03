"""
Jkjob-search Interactive Local Web Dashboard Server.
Features:
- Dark / Light Mode with instant toggle (🌙 / ☀️ icon) and persistent state
- Filter by Work Arrangement: Remote, Hybrid, Onsite/Office, or All
- Filter by Score: All Active, Top Matches (≥85), Applied / In Progress
- Real-time application status update directly into SQLite & CSV
- Pipeline trigger button with live progress
"""
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
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
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --bg-color: #0d1117;
      --card-bg: rgba(22, 27, 34, 0.9);
      --card-border: rgba(48, 54, 61, 0.8);
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --box-bg: rgba(13, 17, 23, 0.7);
      --box-border: #21262d;
      --select-bg: #21262d;
    }
    body.light-theme {
      --bg-color: #f6f8fa;
      --card-bg: #ffffff;
      --card-border: #d0d7de;
      --text-main: #1f2328;
      --text-muted: #656d76;
      --box-bg: #f6f8fa;
      --box-border: #d0d7de;
      --select-bg: #f6f8fa;
    }
    body {
      background-color: var(--bg-color);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      transition: background-color 0.25s ease, color 0.25s ease;
    }
    .glass-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      transition: all 0.25s ease;
    }
    .inner-box {
      background: var(--box-bg);
      border: 1px solid var(--box-border);
    }
    .badge-confirmed { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
    .badge-score { background: rgba(56, 139, 253, 0.15); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4); }
    .badge-arrangement { background: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid rgba(210, 153, 34, 0.4); }
    .badge-status { background: rgba(163, 113, 247, 0.15); color: #bc8cff; border: 1px solid rgba(163, 113, 247, 0.4); }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">
    
    <!-- Top Header -->
    <header class="glass-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold tracking-tight">Jkjob-search</h1>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-900/40 text-emerald-400 border border-emerald-600/40">LIVE INTELLIGENCE</span>
          <span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-900/40 text-blue-400 border border-blue-600/30">REMOTE • HYBRID • ONSITE</span>
        </div>
        <p class="text-sm text-gray-400 mt-1">Opportunity Intelligence & Real-Time Tracking for <span class="font-semibold text-blue-400" id="cand-name">Jeremiah Kariuki Beth</span></p>
      </div>
      
      <div class="flex items-center gap-3 flex-wrap">
        <!-- Theme Toggle Button -->
        <button onclick="toggleTheme()" id="theme-btn" class="p-2.5 glass-card hover:border-gray-500 rounded-lg text-lg transition flex items-center justify-center" title="Toggle Dark/Light Mode">
          <span id="theme-icon">🌙</span>
        </button>

        <!-- Action Buttons -->
        <button onclick="triggerRefresh()" id="refresh-btn" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition shadow flex items-center gap-2">
          <span>🔄 Run Pipeline Now</span>
        </button>
        <a href="/data/job_tracker.csv" download class="px-4 py-2 glass-card hover:border-gray-500 text-sm font-medium rounded-lg transition flex items-center gap-1.5">
          📥 Export CSV
        </a>
      </div>
    </header>

    <!-- Candidate Profile & System Metrics -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Location & Mobility</div>
        <div class="text-base font-bold mt-1">🇰🇪 Nairobi, Kenya</div>
        <div class="text-xs text-gray-400">Open to Remote, Hybrid & Onsite</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Primary Tech Stack</div>
        <div class="text-base font-bold mt-1">Python • Django • React • Odoo</div>
        <div class="text-xs text-gray-400">TypeScript • PostgreSQL • Docker • M-Pesa</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Posting Window</div>
        <div class="text-base font-bold text-emerald-400 mt-1">≤ 48.0 Hours</div>
        <div class="text-xs text-gray-400">Strict publication date verification</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Tracked Vacancies</div>
        <div class="text-base font-bold mt-1" id="total-count">Loading...</div>
        <div class="text-xs text-gray-400" id="applied-count">0 in progress</div>
      </div>
    </div>

    <!-- Filter Control Bar -->
    <div class="glass-card p-4 space-y-3">
      <!-- Status Filters -->
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs font-semibold uppercase text-gray-400 mr-2">Status / Fit:</span>
        <button onclick="setFilter('all')" id="tab-all" class="px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white">All Openings</button>
        <button onclick="setFilter('top')" id="tab-top" class="px-3 py-1.5 rounded-md text-xs font-medium text-gray-400 hover:text-white glass-card">🔥 Top Matches (≥85)</button>
        <button onclick="setFilter('applied')" id="tab-applied" class="px-3 py-1.5 rounded-md text-xs font-medium text-gray-400 hover:text-white glass-card">📝 Applied / Shortlisted</button>
      </div>

      <!-- Arrangement Filters (Remote, Hybrid, Onsite) -->
      <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-800">
        <span class="text-xs font-semibold uppercase text-gray-400 mr-2">Arrangement:</span>
        <button onclick="setArrangement('all')" id="arr-all" class="px-3 py-1 rounded text-xs font-medium bg-gray-700 text-white">All Formats</button>
        <button onclick="setArrangement('Remote')" id="arr-remote" class="px-3 py-1 rounded text-xs font-medium text-gray-400 hover:text-white glass-card">🌐 Remote Only</button>
        <button onclick="setArrangement('Hybrid')" id="arr-hybrid" class="px-3 py-1 rounded text-xs font-medium text-gray-400 hover:text-white glass-card">🏢 Hybrid (Nairobi)</button>
        <button onclick="setArrangement('Onsite')" id="arr-onsite" class="px-3 py-1 rounded text-xs font-medium text-gray-400 hover:text-white glass-card">📍 Onsite / Office</button>
      </div>
    </div>

    <!-- Vacancies List -->
    <div id="jobs-container" class="space-y-4">
      <div class="p-8 text-center text-gray-500">Loading vacancies from SQLite database...</div>
    </div>

  </div>

  <script>
    let currentFilter = 'all';
    let currentArrangement = 'all';
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
    }

    async function loadData() {
      try {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        renderJobs();
      } catch (err) {
        document.getElementById('jobs-container').innerHTML = '<div class="text-red-400 p-4 text-center">Failed to load vacancies from database.</div>';
      }
    }

    function setFilter(f) {
      currentFilter = f;
      ['all', 'top', 'applied'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        if (t === f) {
          el.className = 'px-3 py-1.5 rounded-md text-xs font-medium bg-blue-600 text-white';
        } else {
          el.className = 'px-3 py-1.5 rounded-md text-xs font-medium text-gray-400 hover:text-white glass-card';
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
          el.className = 'px-3 py-1 rounded text-xs font-medium bg-gray-700 text-white';
        } else {
          el.className = 'px-3 py-1 rounded text-xs font-medium text-gray-400 hover:text-white glass-card';
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
        return true;
      });

      document.getElementById('total-count').innerText = allJobs.length + ' Positions';
      const appliedCount = allJobs.filter(j => ['Applied', 'Interviewing'].includes(j.application_status)).length;
      document.getElementById('applied-count').innerText = appliedCount + ' applied / in progress';

      if (!filtered.length) {
        container.innerHTML = '<div class="glass-card p-8 text-center text-gray-400">No positions found matching this combination of filters.</div>';
        return;
      }

      container.innerHTML = filtered.map(j => {
        const arrangementBadge = j.work_arrangement.toLowerCase().includes('remote') 
          ? '🌐 Remote' 
          : (j.work_arrangement.toLowerCase().includes('hybrid') ? '🏢 Hybrid' : '📍 Onsite');

        return `
        <div class="glass-card p-6 space-y-4 hover:border-blue-500/50 transition">
          <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div>
              <div class="flex items-center gap-2.5 flex-wrap">
                <a href="${j.official_application_link}" target="_blank" class="text-lg font-bold hover:text-blue-400 transition flex items-center gap-1.5">
                  ${j.job_title} ↗
                </a>
                <span class="px-2.5 py-0.5 rounded text-xs font-semibold badge-score">Match ${j.match_score}/100</span>
                <span class="px-2.5 py-0.5 rounded text-xs font-semibold badge-arrangement">${arrangementBadge}</span>
                <span class="px-2.5 py-0.5 rounded text-xs font-semibold badge-confirmed">✓ ${j.emea_kenya_eligibility_status.split('(')[0]}</span>
                <span class="px-2 py-0.5 rounded text-xs badge-status">${j.application_status}</span>
              </div>
              <div class="text-sm text-gray-400 mt-1">
                <strong class="text-gray-200">${j.company}</strong> • ${j.seniority} • ${j.employment_type} • 
                <span>${j.eligible_hiring_locations}</span> • 
                <span class="text-yellow-400/90 font-medium">${j.salary_compensation}</span>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="flex items-center gap-2 self-end md:self-auto">
              <select onchange="updateStatus('${j.official_application_link}', this.value)" class="inner-box text-xs px-2.5 py-1.5 rounded focus:outline-none focus:border-blue-500">
                <option value="Not reviewed" ${j.application_status === 'Not reviewed' ? 'selected' : ''}>Not reviewed</option>
                <option value="Shortlisted" ${j.application_status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                <option value="Applied" ${j.application_status === 'Applied' ? 'selected' : ''}>Applied</option>
                <option value="Interviewing" ${j.application_status === 'Interviewing' ? 'selected' : ''}>Interviewing</option>
                <option value="Rejected" ${j.application_status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                <option value="Closed" ${j.application_status === 'Closed' ? 'selected' : ''}>Closed</option>
              </select>
              <a href="${j.official_application_link}" target="_blank" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded transition shadow-sm">
                Apply Official
              </a>
            </div>
          </div>

          <!-- Matching Rationale & Skills Box -->
          <div class="inner-box text-xs p-3.5 rounded-lg space-y-1.5">
            <div><span class="font-semibold text-gray-400">Why it matches:</span> <span class="text-gray-300">${j.reasons_for_match}</span></div>
            ${j.missing_requirements_risks ? `<div><span class="text-amber-400/90 font-semibold">Identified Gaps:</span> <span class="text-gray-400">${j.missing_requirements_risks}</span></div>` : ''}
            <div><span class="font-semibold text-gray-400">Required Stack:</span> <span class="text-blue-300">${j.required_technical_skills}</span></div>
          </div>

          <div class="flex justify-between items-center text-xs text-gray-500 pt-1">
            <span>Posted ~${j.listing_age_hours}h ago via ${j.original_source}</span>
            <span>Recommended Next Step: <strong class="text-blue-400">${j.recommended_next_action}</strong></span>
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
      btn.innerText = '⏳ Running pipeline...';
      btn.disabled = true;
      try {
        await fetch('/api/refresh', { method: 'POST' });
        await loadData();
      } finally {
        btn.innerText = '🔄 Run Pipeline Now';
        btn.disabled = false;
      }
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
            runner = PipelineRunner()
            runner.run()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server(port=8000):
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"[✓] Jkjob-search web dashboard running at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server(8000)

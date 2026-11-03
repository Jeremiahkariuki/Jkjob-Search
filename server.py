"""
Jkjob-search Interactive Local Web Dashboard Server.
Zero extra dependencies - uses Python's built-in http.server.
Endpoints:
  GET  /              - Modern Web UI Dashboard
  GET  /api/jobs      - Returns all tracked jobs from SQLite
  GET  /api/profile   - Returns candidate profile
  POST /api/status    - Updates job application status and notes
  POST /api/refresh   - Triggers fresh search and matching pipeline
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
  <title>Jkjob-search | EMEA Tech Job Intelligence</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .glass-card { background: rgba(22, 27, 34, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(48, 54, 61, 0.7); border-radius: 12px; }
    .badge-confirmed { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
    .badge-score { background: rgba(56, 139, 253, 0.15); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4); }
    .badge-status { background: rgba(163, 113, 247, 0.15); color: #bc8cff; border: 1px solid rgba(163, 113, 247, 0.4); }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">
    
    <!-- Top Header -->
    <header class="glass-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-white tracking-tight">Jkjob-search</h1>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-900/60 text-emerald-400 border border-emerald-700/50">LIVE SYSTEM</span>
        </div>
        <p class="text-sm text-gray-400 mt-1">Dedicated EMEA & Kenya Remote Tech Opportunity Engine for <span class="text-white font-medium" id="cand-name">Jeremiah Kariuki Beth</span></p>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="triggerRefresh()" id="refresh-btn" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition shadow flex items-center gap-2">
          <span>🔄 Run Pipeline Now</span>
        </button>
        <a href="/data/job_tracker.csv" download class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg border border-gray-700 transition">
          📥 Export CSV
        </a>
      </div>
    </header>

    <!-- Profile & Metrics Bar -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Location / Base</div>
        <div class="text-base font-bold text-white mt-1">🇰🇪 Nairobi, Kenya</div>
        <div class="text-xs text-gray-400">Africa/Nairobi (EAT • UTC+3)</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Verified Stack</div>
        <div class="text-base font-bold text-white mt-1">Python • Django • React • Odoo</div>
        <div class="text-xs text-gray-400">TypeScript • PostgreSQL • Docker</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Freshness Window</div>
        <div class="text-base font-bold text-emerald-400 mt-1">≤ 48.0 Hours</div>
        <div class="text-xs text-gray-400">Strict posting timestamp filter</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-xs uppercase text-gray-400 font-semibold">Tracked Vacancies</div>
        <div class="text-base font-bold text-white mt-1" id="total-count">Loading...</div>
        <div class="text-xs text-gray-400" id="applied-count">0 applied</div>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="flex gap-2 border-b border-gray-800 pb-2">
      <button onclick="setFilter('all')" id="tab-all" class="px-3 py-1.5 rounded-md text-sm font-medium bg-gray-800 text-white">All Active</button>
      <button onclick="setFilter('top')" id="tab-top" class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-400 hover:text-white">Top Matches (≥85)</button>
      <button onclick="setFilter('applied')" id="tab-applied" class="px-3 py-1.5 rounded-md text-sm font-medium text-gray-400 hover:text-white">Applied / Interviewing</button>
    </div>

    <!-- Jobs Grid -->
    <div id="jobs-container" class="space-y-4">
      <div class="p-8 text-center text-gray-500">Loading vacancies from SQLite database...</div>
    </div>

  </div>

  <script>
    let currentFilter = 'all';
    let allJobs = [];

    async function loadData() {
      try {
        const res = await fetch('/api/jobs');
        allJobs = await res.json();
        renderJobs();
      } catch (err) {
        document.getElementById('jobs-container').innerHTML = '<div class="text-red-400 p-4 text-center">Failed to load jobs from database.</div>';
      }
    }

    function setFilter(f) {
      currentFilter = f;
      ['all', 'top', 'applied'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        if (t === f) {
          el.className = 'px-3 py-1.5 rounded-md text-sm font-medium bg-gray-800 text-white';
        } else {
          el.className = 'px-3 py-1.5 rounded-md text-sm font-medium text-gray-400 hover:text-white';
        }
      });
      renderJobs();
    }

    function renderJobs() {
      const container = document.getElementById('jobs-container');
      const filtered = allJobs.filter(j => {
        if (currentFilter === 'top') return j.match_score >= 85;
        if (currentFilter === 'applied') return ['Applied', 'Interviewing', 'Shortlisted'].includes(j.application_status);
        return true;
      });

      document.getElementById('total-count').innerText = allJobs.length + ' Positions';
      const appliedCount = allJobs.filter(j => ['Applied', 'Interviewing'].includes(j.application_status)).length;
      document.getElementById('applied-count').innerText = appliedCount + ' applied / in progress';

      if (!filtered.length) {
        container.innerHTML = '<div class="glass-card p-8 text-center text-gray-400">No jobs match this filter criteria.</div>';
        return;
      }

      container.innerHTML = filtered.map(j => `
        <div class="glass-card p-6 space-y-4 hover:border-gray-600 transition">
          <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div>
              <div class="flex items-center gap-3 flex-wrap">
                <a href="${j.official_application_link}" target="_blank" class="text-lg font-bold text-white hover:text-blue-400 transition flex items-center gap-1.5">
                  ${j.job_title} ↗
                </a>
                <span class="px-2.5 py-0.5 rounded text-xs font-semibold badge-score">Match ${j.match_score}/100</span>
                <span class="px-2.5 py-0.5 rounded text-xs font-semibold badge-confirmed">✓ ${j.emea_kenya_eligibility_status.split('(')[0]}</span>
                <span class="px-2 py-0.5 rounded text-xs badge-status">${j.application_status}</span>
              </div>
              <div class="text-sm text-gray-400 mt-1">
                <strong class="text-gray-200">${j.company}</strong> • ${j.seniority} • ${j.employment_type} • 
                <span class="text-gray-300">${j.eligible_hiring_locations}</span> • 
                <span class="text-yellow-400/90 font-medium">${j.salary_compensation}</span>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="flex items-center gap-2 self-end md:self-auto">
              <select onchange="updateStatus('${j.official_application_link}', this.value)" class="bg-gray-800 text-gray-300 text-xs px-2.5 py-1.5 rounded border border-gray-700 focus:outline-none focus:border-blue-500">
                <option value="Not reviewed" ${j.application_status === 'Not reviewed' ? 'selected' : ''}>Not reviewed</option>
                <option value="Shortlisted" ${j.application_status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
                <option value="Applied" ${j.application_status === 'Applied' ? 'selected' : ''}>Applied</option>
                <option value="Interviewing" ${j.application_status === 'Interviewing' ? 'selected' : ''}>Interviewing</option>
                <option value="Rejected" ${j.application_status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                <option value="Closed" ${j.application_status === 'Closed' ? 'selected' : ''}>Closed</option>
              </select>
              <a href="${j.official_application_link}" target="_blank" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition">
                Apply Official
              </a>
            </div>
          </div>

          <!-- Matching Rationale & Skills -->
          <div class="text-xs bg-gray-900/60 p-3 rounded-lg border border-gray-800 space-y-1.5">
            <div><span class="text-gray-400 font-semibold">Why it matches:</span> <span class="text-gray-300">${j.reasons_for_match}</span></div>
            ${j.missing_requirements_risks ? `<div><span class="text-amber-400/90 font-semibold">Gaps / Risks:</span> <span class="text-gray-400">${j.missing_requirements_risks}</span></div>` : ''}
            <div><span class="text-gray-400 font-semibold">Required Tech:</span> <span class="text-blue-300">${j.required_technical_skills}</span></div>
          </div>

          <div class="flex justify-between items-center text-xs text-gray-500 pt-1">
            <span>Discovered: ~${j.listing_age_hours}h ago via ${j.original_source}</span>
            <span>Recommended: <strong class="text-white">${j.recommended_next_action}</strong></span>
          </div>
        </div>
      `).join('');
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

"""Web server for openScience UI."""

from flask import Flask, jsonify, render_template_string

from openscience.core.session import ScienceSession


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Global session (would use proper session management in production)
    session = ScienceSession()

    @app.route("/")
    def index():
        """Serve the main UI."""
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/agents")
    def list_agents():
        """List available agents."""
        agents = []
        for name, agent_class in session.orchestrator.agents.items():
            agents.append(
                {
                    "name": name,
                    "category": agent_class.metadata.category,
                    "description": agent_class.metadata.description,
                }
            )
        return jsonify({"agents": agents})

    @app.route("/api/session/load", methods=["POST"])
    def load_data():
        """Load data into session."""
        from flask import request

        data = request.get_json()

        file_path = data.get("file_path")
        format_hint = data.get("format", "auto")

        try:
            session.load_data(file_path, format=format_hint)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/api/session/analyze", methods=["POST"])
    def analyze():
        """Run analysis task."""
        from flask import request

        data = request.get_json()

        task = data.get("task")
        specialist = data.get("specialist")

        try:
            result = session.analyze(task, specialist=specialist)
            return jsonify({"status": "success", "result": str(result)})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/health")
    def health():
        """Health check endpoint for Docker health checks."""
        return jsonify({"status": "healthy", "service": "openscience-api", "version": "0.1.0"}), 200

    return app


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>openScience — AI Workbench for Scientific Research</title>
    <style>
        :root {
            --bg: #0d1117;
            --panel: #161b22;
            --panel2: #1c2330;
            --border: #2b3645;
            --text: #e6edf3;
            --muted: #8b98a9;
            --accent: #14b8a6;
            --accent2: #0d9488;
            --purple: #818cf8;
            --amber: #f59e0b;
            --green: #10b981;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        .layout { display: flex; min-height: 100vh; }

        /* Sidebar */
        .sidebar {
            width: 240px;
            background: var(--panel);
            border-right: 1px solid var(--border);
            padding: 24px 16px;
            position: sticky;
            top: 0;
            height: 100vh;
            flex-shrink: 0;
        }
        .logo { display: flex; align-items: center; gap: 10px; margin-bottom: 28px; }
        .logo-badge {
            width: 38px; height: 38px; border-radius: 10px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            display: grid; place-items: center; font-size: 20px;
        }
        .logo h1 { font-size: 18px; margin: 0; font-weight: 700; letter-spacing: -0.3px; }
        .logo small { display: block; color: var(--muted); font-size: 11px; font-weight: 400; }
        .nav-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin: 20px 0 8px; }
        .nav-item {
            display: flex; align-items: center; gap: 10px;
            padding: 8px 10px; border-radius: 8px; cursor: pointer;
            color: var(--muted); font-size: 14px; text-decoration: none; margin-bottom: 2px;
        }
        .nav-item.active, .nav-item:hover { background: var(--panel2); color: var(--text); }
        .uptime { margin-top: 28px; padding: 12px; background: var(--panel2); border-radius: 8px; font-size: 12px; color: var(--muted); }
        .uptime b { color: var(--green); }

        /* Main */
        .main { flex: 1; padding: 32px 40px; max-width: 1200px; }
        .hero {
            background: linear-gradient(120deg, rgba(20,184,166,0.15), rgba(129,140,248,0.12));
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 28px;
        }
        .hero h2 { margin: 0 0 6px; font-size: 24px; letter-spacing: -0.4px; }
        .hero p { margin: 0; color: var(--muted); font-size: 14px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
        .stat {
            background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
            padding: 16px 18px;
        }
        .stat .num { font-size: 26px; font-weight: 700; color: var(--accent); }
        .stat .lbl { font-size: 12px; color: var(--muted); margin-top: 2px; }

        .card {
            background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
            padding: 22px 24px; margin-bottom: 24px;
        }
        .card h3 { margin: 0 0 4px; font-size: 16px; }
        .card .sub { color: var(--muted); font-size: 13px; margin-bottom: 16px; }
        .row { display: flex; gap: 12px; }
        .row > * { flex: 1; }
        input, select, textarea {
            width: 100%;
            padding: 11px 14px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 9px;
            color: var(--text);
            font-size: 14px;
            margin: 0;
        }
        input:focus, select:focus { outline: none; border-color: var(--accent); }
        input::placeholder { color: var(--muted); }
        button {
            background: var(--accent); color: #04222a; border: none;
            padding: 11px 22px; border-radius: 9px; cursor: pointer;
            font-weight: 600; font-size: 14px; white-space: nowrap;
            transition: background .15s;
        }
        button:hover { background: #2dd4bf; }
        button:disabled { opacity: 0.5; cursor: wait; }

        #result { margin-top: 16px; display: none; }
        #result.show { display: block; }
        #result pre {
            background: var(--bg); border: 1px solid var(--border); border-radius: 9px;
            padding: 14px; font-size: 12.5px; color: #a5f3ce; overflow-x: auto;
            font-family: 'SF Mono', 'JetBrains Mono', Menlo, monospace;
            max-height: 320px; overflow-y: auto; white-space: pre-wrap;
        }
        #result .ok { border-left: 3px solid var(--green); padding-left: 10px; margin-bottom: 8px; font-size: 13px; }

        .agents-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        #agentFilter { max-width: 220px; }
        .cat-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
        .pill {
            font-size: 12px; padding: 5px 12px; border-radius: 999px; cursor: pointer;
            background: var(--panel2); border: 1px solid var(--border); color: var(--muted);
        }
        .pill.active { background: rgba(20,184,166,0.15); border-color: var(--accent); color: var(--accent); }
        #agents { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
        .agent-card {
            background: var(--panel2); border: 1px solid var(--border);
            padding: 14px 16px; border-radius: 10px;
        }
        .agent-card:hover { border-color: var(--accent); }
        .agent-name { font-weight: 600; font-size: 13.5px; color: var(--accent); font-family: 'SF Mono', Menlo, monospace; }
        .agent-category { font-size: 10.5px; color: var(--amber); text-transform: uppercase; letter-spacing: 0.6px; margin: 3px 0 6px; }
        .agent-desc { font-size: 12.5px; color: var(--muted); line-height: 1.45; }

        @media (max-width: 900px) {
            .sidebar { display: none; }
            .stats { grid-template-columns: repeat(2, 1fr); }
            .main { padding: 20px; }
        }
    </style>
</head>
<body>
<div class="layout">
    <aside class="sidebar">
        <div class="logo">
            <div class="logo-badge">🔬</div>
            <div>
                <h1>openScience</h1>
                <small>AI research workbench</small>
            </div>
        </div>
        <div class="nav-label">Workspace</div>
        <a class="nav-item active">📊 Analysis</a>
        <a class="nav-item">🤖 Agents</a>
        <a class="nav-item">🗄️ Sessions</a>
        <a class="nav-item">📈 Figures</a>
        <div class="nav-label">Resources</div>
        <a class="nav-item" href="/health" target="_blank">❤️ Health</a>
        <a class="nav-item" href="https://yakinrubaiat.github.io/openScience/" target="_blank">📖 Documentation</a>
        <a class="nav-item" href="https://github.com/YakinRubaiat/openScience" target="_blank">🐙 GitHub</a>
        <div class="uptime">API <b>● healthy</b><br><span id="agentCountLine"></span></div>
    </aside>

    <main class="main">
        <div class="hero">
            <h2>Scientific analysis, agent-driven</h2>
            <p>Describe a task — openScience routes it to the right specialized agent across literature, analysis, visualization, and writing.</p>
        </div>

        <div class="stats">
            <div class="stat"><div class="num" id="statAgents">—</div><div class="lbl">Specialized agents</div></div>
            <div class="stat"><div class="num" id="statSkills">270+</div><div class="lbl">Scientific skills</div></div>
            <div class="stat"><div class="num" id="statCats">—</div><div class="lbl">Agent categories</div></div>
            <div class="stat"><div class="num" id="statStatus">●</div><div class="lbl">API status</div></div>
        </div>

        <div class="card">
            <h3>⚡ Quick Analysis</h3>
            <div class="sub">Run a task end-to-end: data loading, analysis, and results — right from the browser.</div>
            <input type="text" id="taskInput" placeholder="e.g. Quality control and clustering of pbmc_3k…" />
            <div class="row" style="margin-top: 12px;">
                <select id="specialistSelect"><option value="">🤖 Auto-select agent</option></select>
                <button onclick="runAnalysis()" id="runBtn">Run Analysis →</button>
            </div>
            <div id="result"></div>
        </div>

        <div class="card">
            <div class="agents-head">
                <div>
                    <h3>🤖 Agent Catalog</h3>
                    <div class="sub">Specialists across the whole research lifecycle</div>
                </div>
                <input type="text" id="agentFilter" placeholder="Filter agents…" oninput="filterAgents()" />
            </div>
            <div class="cat-pills" id="catPills"></div>
            <div id="agents">Loading agents…</div>
        </div>
    </main>
</div>

<script>
    let ALL_AGENTS = [], ACTIVE_CAT = null;

    fetch('/api/agents')
        .then(r => r.json())
        .then(data => {
            ALL_AGENTS = data.agents;
            document.getElementById('statAgents').textContent = ALL_AGENTS.length;
            document.getElementById('agentCountLine').textContent = ALL_AGENTS.length + ' agents loaded';
            const cats = [...new Set(ALL_AGENTS.map(a => a.category))];
            document.getElementById('statCats').textContent = cats.length;
            const pills = document.getElementById('catPills');
            pills.innerHTML = '<span class="pill active" onclick="setCat(null, this)">All</span>' +
                cats.map(c => `<span class="pill" onclick="setCat('${c}', this)">${c}</span>`).join('');
            const select = document.getElementById('specialistSelect');
            ALL_AGENTS.forEach(a => select.innerHTML += `<option value="${a.name}">${a.name}</option>`);
            renderAgents();
        });

    function setCat(cat, el) {
        ACTIVE_CAT = cat;
        document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        el.classList.add('active');
        renderAgents();
    }

    function filterAgents() { renderAgents(); }

    function renderAgents() {
        const q = (document.getElementById('agentFilter').value || '').toLowerCase();
        const list = ALL_AGENTS.filter(a =>
            (!ACTIVE_CAT || a.category === ACTIVE_CAT) &&
            (!q || a.name.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)));
        document.getElementById('agents').innerHTML = list.map(a => `
            <div class="agent-card">
                <div class="agent-name">${a.name}</div>
                <div class="agent-category">${a.category}</div>
                <div class="agent-desc">${a.description || ''}</div>
            </div>`).join('') || '<div style="color:var(--muted)">No agents match.</div>';
    }

    function runAnalysis() {
        const task = document.getElementById('taskInput').value;
        const specialist = document.getElementById('specialistSelect').value;
        if (!task) { document.getElementById('taskInput').focus(); return; }
        const btn = document.getElementById('runBtn');
        btn.disabled = true; btn.textContent = 'Running…';
        const resBox = document.getElementById('result');
        resBox.className = 'show';
        resBox.innerHTML = '<pre>⏳ Executing ' + (specialist || 'auto-selected agent') + '…</pre>';
        fetch('/api/session/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task, specialist})
        })
        .then(r => r.json())
        .then(data => {
            resBox.innerHTML = '<div class="ok">✔ Completed</div><pre>' +
                JSON.stringify(data, null, 2).replace(/</g, '&lt;') + '</pre>';
        })
        .catch(err => { resBox.innerHTML = '<pre>✖ ' + err + '</pre>'; })
        .finally(() => { btn.disabled = false; btn.textContent = 'Run Analysis →'; });
    }

    document.getElementById('taskInput').addEventListener('keydown',
        e => { if (e.key === 'Enter') runAnalysis(); });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import os

    app = create_app()
    # Debug mode must be opt-in via environment; never default to True
    # (Bandit B201: the Werkzeug debugger allows arbitrary code execution).
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"})

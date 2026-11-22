"""Web server for openScience UI."""

from flask import Flask, jsonify, render_template_string

from openscience.core.session import ScienceSession


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Register API blueprint
    from openscience.api import api_bp

    app.register_blueprint(api_bp)

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
<html>
<head>
    <title>openScience</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background: #5568d3;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }
        #agents {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }
        .agent-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .agent-name {
            font-weight: bold;
            color: #667eea;
        }
        .agent-category {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 openScience</h1>
        <p>Open-source AI workbench for scientific research</p>
    </div>
    
    <div class="card">
        <h2>📊 Quick Analysis</h2>
        <input type="text" id="taskInput" placeholder="Describe your analysis task..." />
        <select id="specialistSelect">
            <option value="">Auto-select agent</option>
        </select>
        <button onclick="runAnalysis()">Run Analysis</button>
        <div id="result"></div>
    </div>
    
    <div class="card">
        <h2>🤖 Available Agents</h2>
        <div id="agents">Loading...</div>
    </div>
    
    <script>
        // Load agents on page load
        fetch('/api/agents')
            .then(r => r.json())
            .then(data => {
                const agentsDiv = document.getElementById('agents');
                const select = document.getElementById('specialistSelect');
                
                data.agents.forEach(agent => {
                    // Add to grid
                    agentsDiv.innerHTML += `
                        <div class="agent-card">
                            <div class="agent-name">${agent.name}</div>
                            <div class="agent-category">${agent.category}</div>
                            <div>${agent.description}</div>
                        </div>
                    `;
                    
                    // Add to select
                    select.innerHTML += `<option value="${agent.name}">${agent.name}</option>`;
                });
            });
        
        function runAnalysis() {
            const task = document.getElementById('taskInput').value;
            const specialist = document.getElementById('specialistSelect').value;
            
            fetch('/api/session/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task, specialist})
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('result').innerHTML = 
                    `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
        }
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

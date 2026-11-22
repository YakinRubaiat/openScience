"""REST API endpoints for openScience."""

from flask import Blueprint, jsonify, request

from openscience.core.session import ScienceSession

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/v1/agents", methods=["GET"])
def list_agents():
    """List all available agents."""
    session = ScienceSession()
    agents = []
    for name, agent_class in session.orchestrator.agents.items():
        agents.append(
            {
                "name": name,
                "category": agent_class.metadata.category,
                "description": agent_class.metadata.description,
            }
        )
    return jsonify({"agents": agents, "count": len(agents)})


@api_bp.route("/v1/tasks/submit", methods=["POST"])
def submit_task():
    """Submit a task for background processing."""
    data = request.get_json()

    # Validate request
    if not data or "task" not in data:
        return jsonify({"error": "Missing 'task' parameter"}), 400

    # Import here to avoid circular dependency
    from openscience.workers.tasks import analyze_data_task

    # Submit task to Celery
    task = analyze_data_task.delay(
        file_path=data.get("file_path"),
        task_description=data.get("task"),
        specialist=data.get("specialist"),
    )

    return jsonify({"status": "submitted", "task_id": task.id}), 202


@api_bp.route("/v1/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Get the status of a background task."""
    from openscience.workers.tasks import celery_app

    task = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task.status,
    }

    if task.successful():
        response["result"] = task.result
    elif task.failed():
        response["error"] = str(task.info)

    return jsonify(response)


@api_bp.route("/v1/health", methods=["GET"])
def health_check():
    """API health check endpoint."""
    return (
        jsonify(
            {
                "status": "healthy",
                "service": "openscience-api",
                "version": "0.1.0",
                "api_version": "v1",
            }
        ),
        200,
    )

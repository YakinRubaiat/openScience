"""Tests for openscience workers."""

import pytest

celery = pytest.importorskip("celery", reason="celery not installed")

from openscience.workers.tasks import celery_app, health_check  # noqa: E402


def test_celery_app_config():
    """Test Celery app configuration."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.enable_utc is True


def test_health_check_task():
    """Test health check task."""
    result = health_check()
    assert result["status"] == "healthy"

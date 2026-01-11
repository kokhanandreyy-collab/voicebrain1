
from fastapi.testclient import TestClient
from app.main import app

def test_metrics_expose():
    """Test that /metrics endpoint is exposed and contains custom metrics."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "db_queries_total" in response.text
    assert "reflection_ops_total" in response.text
    assert "memory_graph_nodes" in response.text

# Note: We can't easily test Sentry init without mocking or credentials, 
# but we can assume it loads if no error.

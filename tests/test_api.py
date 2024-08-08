from fastapi.testclient import TestClient
from app.api import app  # Import the FastAPI app

# Create a TestClient instance
client = TestClient(app)


def test_export_csv():
    response = client.get("/export", params={"output_format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"


def test_export_json():
    response = client.get("/export", params={"output_format": "json"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_export_parquet():
    response = client.get("/export", params={"output_format": "parquet"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"


def test_export_with_filters():
    response = client.get(
        "/export",
        params={
            "start_timestamp": "2023-01-01T00:00:00",
            "end_timestamp": "2023-12-31T23:59:59",
            "batch_id": "some-batch-id",
            "batch_name": "some-batch-name",
            "output_format": "json",
        },
    )
    assert response.status_code in [200, 404]  # 404 if no data matches the filters


def test_invalid_output_format():
    response = client.get("/export", params={"output_format": "xml"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid output format specified"}

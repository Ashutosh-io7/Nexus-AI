import io
from fastapi import status


def test_preview_endpoint(client):
    csv_bytes = b"client_id,customer_name,mrr\nCL-01,Test Corp,450.00\n"
    response = client.post(
        "/api/v1/customers/upload-preview",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_columns"] == 3
    assert data["detected_mappings"]["client_id"] == "external_id"
    assert data["detected_mappings"]["customer_name"] == "full_name"
    assert data["detected_mappings"]["mrr"] == "monthly_revenue"
    assert len(data["sample_rows"]) == 1


def test_preview_non_csv_rejected(client):
    response = client.post(
        "/api/v1/customers/upload-preview",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Only CSV files" in response.json()["detail"]


def test_upload_endpoint_and_audit(client):
    csv_bytes = b"""customer_id,name,email,monthly_revenue,churned
CUST-10,Alpha,alpha@test.com,100.00,0
CUST-20,Beta,beta@test.com,200.00,1
"""
    # 1. Upload CSV
    response = client.post(
        "/api/v1/customers/upload",
        files={"file": ("customers.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert response.status_code == status.HTTP_201_CREATED
    import_data = response.json()
    assert import_data["status"] == "completed"
    assert import_data["inserted_count"] == 2
    assert import_data["failed_count"] == 0
    import_id = import_data["id"]

    # 2. Query import history
    list_res = client.get("/api/v1/customers/imports")
    assert list_res.status_code == status.HTTP_200_OK
    history = list_res.json()
    assert len(history) >= 1
    assert any(h["id"] == import_id for h in history)

    # 3. Query specific import
    detail_res = client.get(f"/api/v1/customers/imports/{import_id}")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.json()["filename"] == "customers.csv"

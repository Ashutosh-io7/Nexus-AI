def test_user_registration_and_login(client):
    # 1. Register a new user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sarah.csm@nexus.ai",
            "password": "SecurePassword123!",
            "full_name": "Sarah Connor",
            "role": "csm",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "sarah.csm@nexus.ai"
    assert reg_data["user"]["role"] == "csm"

    # 2. Login with correct password
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.csm@nexus.ai", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["access_token"]

    # 3. Access /me endpoint with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "sarah.csm@nexus.ai"


def test_login_invalid_password(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@nexus.ai", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_protected_me_without_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
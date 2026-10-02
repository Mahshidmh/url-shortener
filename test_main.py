from fastapi.testclient import TestClient


def test_create_url(client):
    response = client.post("/urls", json={"original_url": "https://example.com"})
    assert response.status_code == 201

    data = response.json()
    assert data["short_code"] is not None
    assert len(data["short_code"]) > 0
    assert data["original_url"] == "https://example.com/"

def test_list_urls(client):
    client.post("/urls", json={"original_url": "https://example.com"})
    client.post("/urls", json={"original_url": "https://example.com"})

    response = client.get("/urls")
    assert response.status_code == 200


    data = response.json()
    assert len(data) == 2

def test_update_url(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com"})
    code = create_response.json()["short_code"]
    response = client.patch(f"/urls/{code}", json={"original_url": "https://different-example.com"})
    assert response.status_code == 200

    data = response.json()
    assert data["original_url"] is not None
    assert data["original_url"] == "https://different-example.com/"

def test_update_url_not_found(client):
    response = client.patch("/urls/donotexist", json={"original_url": "https://example.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Short code not found"

def test_delete_url(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com"})
    code  = create_response.json()["short_code"]
    response = client.delete(f"/urls/{code}")
    assert response.status_code == 204

    response2 = client.patch(f"/urls/{code}", json={"original_url": "https://defferent-example.com"})
    assert response2.status_code == 404

def test_delete_url_not_found(client):
    response = client.delete("/urls/donotexist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short code not found"

def test_redirect_to_url(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com"})
    code  = create_response.json()["short_code"]
    response= client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"

def test_redirect_not_found(client):
    response = client.get(f"/donotexist", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Short code not found"

def test_click_count_and_stats(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com"})
    code  = create_response.json()["short_code"]
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)

    response = client.get(f"/urls/{code}/stats")
    assert response.status_code == 200
    assert response.json()["click_count"] == 2

def test_redirect_expired_link(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com", "expires_at" : "2020-01-01T00:00:00Z"})
    code = create_response.json()["short_code"]
    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 410
    assert response.json()["detail"] == "Link is expired or not found!"

def test_redirect_valid_expiration(client):
    create_response = client.post("/urls", json={"original_url": "https://example.com", "expires_at" : "2040-01-01T00:00:00Z"})
    code = create_response.json()["short_code"]
    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/"

def test_rate_limit_exceeded(client):
    for i in range(5):
        response = client.post("/urls", json={"original_url": "https://example.com"})
        assert response.status_code == 201

    response = client.post("/urls", json={"original_url": "https://example.com"})
    assert response.status_code == 429

def test_create_url_invalid_url(client):
    create_response = client.post("/urls", json={"original_url":"not-a-valid-url"})

    assert create_response.status_code == 422

def test_create_url_without_api_key(anon_client):
    response = anon_client.post("/urls", json={"original_url": "https://example.com"})
    assert response.status_code == 401

def test_create_url_wrong_api_key(client):
    response = client.post(
        "/urls",
        json={"original_url": "https://example.com"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"

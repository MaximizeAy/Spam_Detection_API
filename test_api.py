from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_home():

    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "Spam Detection API is running"
    }


def test_spam_prediction():

    response = client.post(
        "/predict",
        json={
            "message": "Congratulations! You've won $1000. Click here."
        }
    )

    assert response.status_code == 200

    data = response.json()

    # Check the response structure
    assert "prediction" in data
    assert "confidence" in data
    assert "features" in data
    assert "message_length" in data
    assert "prediction_time_ms" in data

    # Check fixed values
    assert data["model"] == "Soft Voting Ensemble"
    assert data["version"] == "1.0.0"
    assert "has_url" in data["features"]
    assert "url_count" in data["features"]
    assert "security_keyword_count" in data["features"]
    assert "urgency_count" in data["features"]

def test_invalid_request():

    response = client.post(
        "/predict",
        json={}
    )

    assert response.status_code == 422



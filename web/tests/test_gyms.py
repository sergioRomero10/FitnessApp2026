import pytest
import requests

from fitnessapp.services import gyms


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_cache():
    gyms._CACHE.clear()


def test_search_sends_params_user_agent_and_timeout(monkeypatch, client):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            [
                {
                    "name": "Gym Las Palmas",
                    "lat": "28.1",
                    "lon": "-15.4",
                    "display_name": "Gym Las Palmas, Calle Mayor 1, Las Palmas",
                }
            ]
        )

    monkeypatch.setattr(gyms.requests, "get", fake_get)
    html = client.get("/gyms/", query_string={"city": "Las Palmas & Co"}).data.decode()

    url, kwargs = calls[0]
    assert url.endswith("/search")
    assert kwargs["params"]["q"] == "[leisure=fitness_centre] Las Palmas & Co"  # sin romper la URL
    assert kwargs["headers"]["User-Agent"].startswith("FitnessApp")
    assert kwargs["timeout"] == 10
    assert "Gym Las Palmas" in html and "Calle Mayor 1, Las Palmas" in html


def test_results_are_cached(monkeypatch, client):
    calls = []
    monkeypatch.setattr(gyms.requests, "get", lambda *a, **k: calls.append(1) or FakeResponse([]))
    client.get("/gyms/?city=Madrid")
    client.get("/gyms/?city=madrid")
    assert len(calls) == 1


def test_service_error_shows_message(monkeypatch, client):
    def boom(*_a, **_k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(gyms.requests, "get", boom)
    response = client.get("/gyms/?city=Madrid")
    assert response.status_code == 200
    assert "not available right now" in response.data.decode()


def test_no_results(monkeypatch, client):
    monkeypatch.setattr(gyms.requests, "get", lambda *a, **k: FakeResponse([]))
    assert "No gyms found" in client.get("/gyms/?city=Nowhere").data.decode()

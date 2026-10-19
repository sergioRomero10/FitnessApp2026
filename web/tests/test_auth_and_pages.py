import pytest

from fitnessapp import create_app


def test_app_refuses_to_start_without_secret_key():
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": ""})


def test_public_pages_load(client):
    for url in ("/", "/about", "/gyms/", "/login", "/healthz"):
        assert client.get(url).status_code == 200, url


def test_protected_pages_redirect_to_login(client):
    for url in ("/favorites/", "/diets/", "/diets/calendar", "/diets/events.json"):
        response = client.get(url)
        assert response.status_code == 302, url
        assert "/login" in response.headers["Location"]


def test_guest_login_and_logout(guest, db):
    user = db.users.find_one({"is_guest": True})
    assert user is not None and user["expires_at"] is not None
    assert guest.get("/favorites/").status_code == 200

    assert guest.post("/logout").status_code == 302
    assert guest.get("/favorites/").status_code == 302


def test_guest_login_disabled_when_demo_mode_off(app, client):
    app.config["DEMO_MODE"] = False
    assert client.post("/auth/guest").status_code == 404
    assert b"Try it as a guest" not in client.get("/login").data


def test_google_button_hidden_without_credentials(client):
    assert b"Continue with Google" not in client.get("/login").data
    assert client.get("/auth/google").status_code == 404


def test_next_parameter_cannot_redirect_to_another_site(client):
    response = client.post("/auth/guest", data={"next": "https://evil.example.com/"})
    assert response.headers["Location"] == "/"


def test_next_parameter_returns_to_same_site(client):
    response = client.post("/auth/guest", data={"next": "/diets/"})
    assert response.headers["Location"] == "/diets/"


def test_unknown_page_returns_404_template(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_csrf_is_enforced(make_app):
    app = make_app(WTF_CSRF_ENABLED=True)
    client = app.test_client()
    response = client.post("/auth/guest")
    assert response.status_code == 400

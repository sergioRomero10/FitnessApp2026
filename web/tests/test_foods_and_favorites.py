from conftest import APPLE, BANANA


def test_search_by_name(client):
    html = client.get("/?q=appl").data.decode()
    assert "Apple" in html and "Apple Juice" in html
    assert "Banana" not in html


def test_search_text_is_not_a_regex(client):
    # Antes no había búsqueda en servidor; ahora el texto se escapa
    assert client.get("/?q=.*").status_code == 200
    assert "No foods found" in client.get("/?q=.*").data.decode()


def test_filter_by_category(client):
    html = client.get("/?category=Fruits").data.decode()
    assert "Banana" in html and "Almonds" not in html


def test_pagination(app, client):
    app.config["FOODS_PER_PAGE"] = 2
    html = client.get("/?page=2").data.decode()
    assert 'aria-label="Pagination"' in html
    assert client.get("/?page=999").status_code == 200  # se ajusta a la última página


def test_toggle_favorite_json(guest, db):
    response = guest.post(
        "/favorites/toggle", data={"key": APPLE}, headers={"Accept": "application/json"}
    )
    assert response.get_json() == {"favorite": True}
    assert db.users.find_one({"is_guest": True})["favorites"] == [APPLE]

    response = guest.post(
        "/favorites/toggle", data={"key": APPLE}, headers={"Accept": "application/json"}
    )
    assert response.get_json() == {"favorite": False}
    assert db.users.find_one({"is_guest": True})["favorites"] == []


def test_toggle_unknown_food_is_rejected(guest):
    assert guest.post("/favorites/toggle", data={"key": "nope/nope"}).status_code == 400


def test_toggle_requires_login(client):
    response = client.post(
        "/favorites/toggle", data={"key": APPLE}, headers={"Accept": "application/json"}
    )
    assert response.status_code == 401


def test_favorites_page_lists_and_removes(guest):
    guest.post("/favorites/toggle", data={"key": BANANA})
    assert "Banana" in guest.get("/favorites/").data.decode()

    guest.post("/favorites/remove", data={"key": BANANA})
    assert "any favourite foods yet" in guest.get("/favorites/").data.decode()

import re

from conftest import APPLE, BANANA


def _create_diet(client, name="Cut", start="2026-10-01", end="2026-10-07"):
    response = client.post("/diets/", data={"name": name, "start_date": start, "end_date": end})
    assert response.status_code == 302
    return re.search(r"/diets/([0-9a-f]{24})$", response.headers["Location"]).group(1)


def _favorite(client, key):
    client.post("/favorites/toggle", data={"key": key})


def test_create_and_view_diet(guest):
    diet_id = _create_diet(guest, name="Cut. $week")  # '.' y '$' rompían el original
    html = guest.get(f"/diets/{diet_id}").data.decode()
    assert "Cut. $week" in html
    assert "Cut. $week" in guest.get("/diets/").data.decode()


def test_end_before_start_is_rejected(guest, db):
    guest.post(
        "/diets/", data={"name": "Bad", "start_date": "2026-10-10", "end_date": "2026-10-01"}
    )
    assert db.diets.count_documents({}) == 0


def test_add_food_sums_grams_and_computes_calories(guest):
    _favorite(guest, APPLE)
    _favorite(guest, BANANA)
    diet_id = _create_diet(guest)

    guest.post(f"/diets/{diet_id}/items", data={"food": APPLE, "grams": "100"})
    guest.post(f"/diets/{diet_id}/items", data={"food": APPLE, "grams": "50"})
    guest.post(f"/diets/{diet_id}/items", data={"food": BANANA, "grams": "200"})

    html = guest.get(f"/diets/{diet_id}").data.decode()
    assert "150 g" in html  # 100 + 50 de manzana en una sola línea
    assert "78" in html  # 52 kcal * 1.5
    assert "256" in html  # total: 78 + 178


def test_only_favorites_can_be_added(guest, db):
    diet_id = _create_diet(guest)
    guest.post(f"/diets/{diet_id}/items", data={"food": APPLE, "grams": "100"})
    assert db.diets.find_one()["items"] == []


def test_invalid_grams_do_not_crash(guest, db):
    _favorite(guest, APPLE)
    diet_id = _create_diet(guest)
    for grams in ("", "abc", "-5", "999999"):
        response = guest.post(f"/diets/{diet_id}/items", data={"food": APPLE, "grams": grams})
        assert response.status_code == 302
    assert db.diets.find_one()["items"] == []


def test_remove_item_edit_and_delete(guest, db):
    _favorite(guest, APPLE)
    diet_id = _create_diet(guest)
    guest.post(f"/diets/{diet_id}/items", data={"food": APPLE, "grams": "100"})
    guest.post(f"/diets/{diet_id}/items/remove", data={"key": APPLE})
    assert db.diets.find_one()["items"] == []

    guest.post(
        f"/diets/{diet_id}/edit",
        data={"name": "Bulk", "start_date": "2026-11-01", "end_date": "2026-11-30"},
    )
    diet = db.diets.find_one()
    assert (diet["name"], diet["start_date"], diet["end_date"]) == (
        "Bulk",
        "2026-11-01",
        "2026-11-30",
    )

    guest.post(f"/diets/{diet_id}/delete")
    assert db.diets.count_documents({}) == 0


def test_users_cannot_see_other_users_diets(app, guest):
    diet_id = _create_diet(guest)
    other = app.test_client()
    other.post("/auth/guest")
    assert other.get(f"/diets/{diet_id}").status_code == 404
    other.post(f"/diets/{diet_id}/delete")
    assert guest.get(f"/diets/{diet_id}").status_code == 200


def test_invalid_diet_id_is_404(guest):
    assert guest.get("/diets/not-an-id").status_code == 404


def test_calendar_events(guest):
    diet_id = _create_diet(guest, name="Week 1")
    events = guest.get("/diets/events.json").get_json()
    assert events == [
        {
            "id": diet_id,
            "title": "Week 1",
            "start": "2026-10-01",
            "end": "2026-10-07",
            "allDay": True,
            "url": f"/diets/{diet_id}",
        }
    ]


def test_guest_diets_expire_with_the_guest(guest, db):
    _create_diet(guest)
    assert db.diets.find_one()["expires_at"] == db.users.find_one()["expires_at"]

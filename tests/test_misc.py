import re
from app import bulk_seed


def register_and_login(client, username="testuser", password="password1"):
    client.post("/register", data={
        "username": username, "password": password, "confirm_password": password
    }, follow_redirects=True)
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_register_get(client):
    r = client.get("/register")
    assert r.status_code == 200


def test_register_duplicate_username(client):
    client.post("/register", data={
        "username": "testuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    r = client.post("/register", data={
        "username": "testuser", "password": "password2", "confirm_password": "password2"
    }, follow_redirects=True)
    assert b"Username already exists" in r.data


def test_login_get(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_login_success_page(client):
    register_and_login(client)
    r = client.get("/login-success")
    assert r.status_code == 200


def test_logout_post(client):
    register_and_login(client)
    r = client.post("/logout", follow_redirects=True)
    assert b"Logout successful!" in r.data


def test_dashboard_filter_by_status(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "Open Ticket", "description": "d", "priority": "High"}, follow_redirects=True)
    r = client.get("/?status=Open")
    assert b"Open Ticket" in r.data
    r = client.get("/?status=Resolved")
    assert b"Open Ticket" not in r.data


def test_dashboard_filter_by_priority(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "High Priority Ticket", "description": "d", "priority": "High"}, follow_redirects=True)
    r = client.get("/?priority=High")
    assert b"High Priority Ticket" in r.data
    r = client.get("/?priority=Low")
    assert b"High Priority Ticket" not in r.data


def test_edit_ticket_get(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "Edit Test Ticket", "description": "Desc", "priority": "High"}, follow_redirects=True)
    dash = client.get("/")
    match = re.search(rb'/edit_ticket/(\d+)', dash.data)
    r = client.get(f"/edit_ticket/{match.group(1).decode()}")
    assert r.status_code == 200
    assert b"Edit Test Ticket" in r.data


def test_user_cannot_delete_another_users_ticket(client):
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "Protected Ticket", "description": "d", "priority": "Low"}, follow_redirects=True)
    dash = client.get("/")
    match = re.search(rb'/delete_ticket/(\d+)', dash.data)
    ticket_id = match.group(1).decode()
    client.get("/logout", follow_redirects=True)
    register_and_login(client, "user2x", "password2")
    r = client.post(f"/delete_ticket/{ticket_id}", follow_redirects=True)
    assert b"do not have permission" in r.data


def test_bulk_seed_creates_users_and_tickets(client):
    with client.application.app_context():
        from models import User, Ticket
        bulk_seed()
        assert User.query.count() > 0
        assert Ticket.query.count() > 0


def test_bulk_seed_skips_users_if_already_exist(client):
    with client.application.app_context():
        from models import User, Ticket
        bulk_seed()
        user_count_after_first = User.query.count()
        bulk_seed()
        assert User.query.count() == user_count_after_first
        assert Ticket.query.count() > 10

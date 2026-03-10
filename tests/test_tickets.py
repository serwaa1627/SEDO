import re
from models import User, db


def register_and_login(client, username="testuser", password="password1"):
    client.post("/register", data={
        "username": username, "password": password, "confirm_password": password
    }, follow_redirects=True)
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_create_ticket(client):
    register_and_login(client)
    r = client.post("/new_ticket", data={"title": "My Ticket", "description": "Details", "priority": "High"}, follow_redirects=True)
    assert b"Ticket created successfully!" in r.data
    assert b"My Ticket" in r.data


def test_view_ticket(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "View Me", "description": "Desc", "priority": "Low"}, follow_redirects=True)
    dash = client.get("/", follow_redirects=True)
    match = re.search(rb'/view_ticket/(\d+)', dash.data)
    assert match
    r = client.get(f"/view_ticket/{match.group(1).decode()}", follow_redirects=True)
    assert b"View Me" in r.data


def test_edit_ticket(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "Edit Me", "description": "Desc", "priority": "High"}, follow_redirects=True)
    dash = client.get("/", follow_redirects=True)
    match = re.search(rb'/edit_ticket/(\d+)', dash.data)
    assert match
    r = client.post(f"/edit_ticket/{match.group(1).decode()}", data={
        "title": "Edited Title", "description": "Updated desc", "status": "Open"
    }, follow_redirects=True)
    assert b"Edited Title" in r.data


def test_delete_ticket(client):
    register_and_login(client)
    client.post("/new_ticket", data={"title": "Delete Me", "description": "Desc", "priority": "Low"}, follow_redirects=True)
    dash = client.get("/", follow_redirects=True)
    match = re.search(rb'/delete_ticket/(\d+)', dash.data)
    assert match
    client.post(f"/delete_ticket/{match.group(1).decode()}", follow_redirects=True)
    dash2 = client.get("/", follow_redirects=True)
    assert b"Delete Me" not in dash2.data


def test_user_cannot_edit_another_users_ticket(client):
    # user1 creates a ticket
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "User1 Ticket", "description": "d", "priority": "Low"}, follow_redirects=True)
    dash = client.get("/", follow_redirects=True)
    match = re.search(rb'/edit_ticket/(\d+)', dash.data)
    ticket_id = match.group(1).decode()
    client.get("/logout", follow_redirects=True)

    # user2 tries to edit it — should get 403
    register_and_login(client, "user2x", "password2")
    r = client.get(f"/edit_ticket/{ticket_id}", follow_redirects=True)
    assert r.status_code == 403


def test_admin_can_change_ticket_status(client):
    # user1 creates a ticket
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "Status Ticket", "description": "d", "priority": "High"}, follow_redirects=True)
    dash = client.get("/", follow_redirects=True)
    match = re.search(rb'/edit_ticket/(\d+)', dash.data)
    ticket_id = match.group(1).decode()
    client.get("/logout", follow_redirects=True)

    # register and promote admin
    register_and_login(client, "adminuser", "adminpass1")
    with client.application.app_context():
        u = User.query.filter_by(username="adminuser").first()
        u.role = "admin"
        db.session.commit()
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "adminuser", "password": "adminpass1"}, follow_redirects=True)

    r = client.post(f"/edit_ticket/{ticket_id}", data={
        "title": "Status Ticket", "description": "d", "status": "Resolved"
    }, follow_redirects=True)
    assert b"Resolved" in r.data

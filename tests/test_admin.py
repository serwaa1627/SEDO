from models import User, Ticket, db


def register_and_login(client, username="testuser", password="password1"):
    client.post("/register", data={
        "username": username, "password": password, "confirm_password": password
    }, follow_redirects=True)
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def promote_to_admin(client, username):
    u = User.query.filter_by(username=username).first()
    u.role = "admin"
    db.session.commit()


def test_admin_can_view_users_page(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    r = client.get("/admin/users")
    assert r.status_code == 200
    assert b"adminuser" in r.data


def test_admin_users_filter_by_role_user(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    client.post("/register", data={
        "username": "regularuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    r = client.get("/admin/users?role=user")
    assert r.status_code == 200
    assert b"regularuser" in r.data


def test_admin_users_filter_by_role_admin(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    r = client.get("/admin/users?role=admin")
    assert r.status_code == 200
    assert b"adminuser" in r.data


def test_toggle_role_non_admin_blocked(client):
    client.post("/register", data={
        "username": "targetuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    with client.application.app_context():
        target_id = User.query.filter_by(username="targetuser").first().id
    register_and_login(client, "plainuser", "password1")
    r = client.post(f"/admin/users/{target_id}/toggle_role", follow_redirects=True)
    assert r.status_code == 403


def test_toggle_role_success(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    client.post("/register", data={
        "username": "targetuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    with client.application.app_context():
        target_id = User.query.filter_by(username="targetuser").first().id
    r = client.post(f"/admin/users/{target_id}/toggle_role", follow_redirects=True)
    assert r.status_code == 200
    assert b"role updated to" in r.data


def test_toggle_role_self_prevention(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    with client.application.app_context():
        admin_id = User.query.filter_by(username="adminuser").first().id
    r = client.post(f"/admin/users/{admin_id}/toggle_role", follow_redirects=True)
    assert b"change your own role" in r.data


def test_admin_delete_user_non_admin_blocked(client):
    client.post("/register", data={
        "username": "victim", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    with client.application.app_context():
        victim_id = User.query.filter_by(username="victim").first().id
    register_and_login(client, "plainuser", "password1")
    r = client.post(f"/admin/users/{victim_id}/delete", follow_redirects=True)
    assert r.status_code == 403


def test_admin_delete_user_success(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    client.post("/register", data={
        "username": "deleteuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    with client.application.app_context():
        target_id = User.query.filter_by(username="deleteuser").first().id
    r = client.post(f"/admin/users/{target_id}/delete", follow_redirects=True)
    assert b"has been removed" in r.data


def test_admin_delete_user_self_prevention(client):
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    with client.application.app_context():
        admin_id = User.query.filter_by(username="adminuser").first().id
    r = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=True)
    assert b"delete your own account" in r.data


def test_admin_sees_all_tickets_on_dashboard(client):
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "User1 Ticket", "description": "d", "priority": "Low"}, follow_redirects=True)
    client.get("/logout", follow_redirects=True)
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    r = client.get("/")
    assert b"User1 Ticket" in r.data


def test_admin_can_view_any_ticket(client):
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "Private Ticket", "description": "d", "priority": "Low"}, follow_redirects=True)
    client.get("/logout", follow_redirects=True)
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    with client.application.app_context():
        ticket_id = Ticket.query.filter_by(title="Private Ticket").first().id
    r = client.get(f"/view_ticket/{ticket_id}")
    assert r.status_code == 200
    assert b"Private Ticket" in r.data


def test_admin_can_delete_any_ticket(client):
    register_and_login(client, "user1x", "password1")
    client.post("/new_ticket", data={"title": "Delete Ticket", "description": "d", "priority": "Low"}, follow_redirects=True)
    client.get("/logout", follow_redirects=True)
    register_and_login(client, "adminuser", "adminpass1")
    promote_to_admin(client, "adminuser")
    with client.application.app_context():
        ticket_id = Ticket.query.filter_by(title="Delete Ticket").first().id
    r = client.post(f"/delete_ticket/{ticket_id}", follow_redirects=True)
    assert b"Ticket successfully deleted!" in r.data

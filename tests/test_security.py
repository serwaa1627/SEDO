def test_security_headers_present(client):
    r = client.get("/login")
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in r.headers
    assert "Referrer-Policy" in r.headers


def test_unauthenticated_routes_redirect_to_login(client):
    for route in ["/", "/new_ticket", "/account_settings"]:
        r = client.get(route, follow_redirects=False)
        assert r.status_code == 302, f"{route} should redirect unauthenticated users"


def test_admin_panel_blocked_for_regular_user(client):
    client.post("/register", data={
        "username": "plainuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    client.post("/login", data={"username": "plainuser", "password": "password1"}, follow_redirects=True)
    r = client.get("/admin/users")
    assert r.status_code == 403


def test_user_cannot_view_another_users_ticket(client):
    # user1 creates ticket
    client.post("/register", data={"username": "user1x", "password": "password1", "confirm_password": "password1"}, follow_redirects=True)
    client.post("/login", data={"username": "user1x", "password": "password1"}, follow_redirects=True)
    client.post("/new_ticket", data={"title": "Private", "description": "d", "priority": "Low"}, follow_redirects=True)
    client.get("/logout", follow_redirects=True)

    # user2 tries to access it directly
    client.post("/register", data={"username": "user2x", "password": "password2", "confirm_password": "password2"}, follow_redirects=True)
    client.post("/login", data={"username": "user2x", "password": "password2"}, follow_redirects=True)
    r = client.get("/view_ticket/1", follow_redirects=True)
    assert r.status_code == 403


def test_404_returns_custom_page(client):
    r = client.get("/this-does-not-exist")
    assert r.status_code == 404
    assert b"404" in r.data

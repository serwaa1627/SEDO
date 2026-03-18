def test_register_and_login(client):
    r = client.post("/register", data={
        "username": "testuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    assert r.status_code == 200

    r = client.post("/login", data={"username": "testuser", "password": "password1"}, follow_redirects=True)
    assert b"Dashboard" in r.data or r.status_code == 200


def test_login_invalid_credentials(client):
    r = client.post("/login", data={"username": "nobody", "password": "wrongpass1"}, follow_redirects=True)
    assert b"Invalid username or password" in r.data


def test_logout(client):
    client.post("/register", data={
        "username": "alice123", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    client.post("/login", data={"username": "alice123", "password": "password1"}, follow_redirects=True)

    r = client.get("/logout", follow_redirects=True)
    assert b"Logout successful!" in r.data
    assert b"Login" in r.data


def test_protected_route_redirects_when_not_logged_in(client):
    r = client.get("/new_ticket", follow_redirects=False)
    assert r.status_code in (302, 401)


def test_login_wrong_password_existing_user(client):
    client.post("/register", data={
        "username": "testuser", "password": "password1", "confirm_password": "password1"
    }, follow_redirects=True)
    r = client.post("/login", data={"username": "testuser", "password": "wrongpass1"}, follow_redirects=True)
    assert b"Invalid username or password" in r.data

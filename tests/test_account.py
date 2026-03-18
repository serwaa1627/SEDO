def register_and_login(client, username="testuser", password="password1"):
    client.post("/register", data={
        "username": username, "password": password, "confirm_password": password
    }, follow_redirects=True)
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_account_settings_get(client):
    register_and_login(client)
    r = client.get("/account_settings")
    assert r.status_code == 200


def test_change_password_success(client):
    register_and_login(client)
    r = client.post("/account_settings", data={
        "current_password": "password1",
        "new_password": "newpassword1",
        "confirm_password": "newpassword1"
    }, follow_redirects=True)
    assert b"Password updated successfully" in r.data


def test_change_password_wrong_current(client):
    register_and_login(client)
    r = client.post("/account_settings", data={
        "current_password": "wrongpassword",
        "new_password": "newpassword1",
        "confirm_password": "newpassword1"
    }, follow_redirects=True)
    assert b"Incorrect current password" in r.data

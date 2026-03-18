from models import User, Ticket, db


def test_user_is_admin_true(client):
    with client.application.app_context():
        user = User(username="admintest", password="hash", role="admin", is_deleted=False)
        db.session.add(user)
        db.session.commit()
        assert user.is_admin() is True


def test_user_is_admin_false(client):
    with client.application.app_context():
        user = User(username="regulartest", password="hash", role="user", is_deleted=False)
        db.session.add(user)
        db.session.commit()
        assert user.is_admin() is False


def test_set_and_check_password(client):
    with client.application.app_context():
        user = User(username="pwdtest", password="placeholder", role="user", is_deleted=False)
        db.session.add(user)
        db.session.commit()
        user.set_password("mysecurepassword1")
        db.session.commit()
        assert user.check_password("mysecurepassword1") is True
        assert user.check_password("wrongpassword") is False


def test_ticket_relationships(client):
    with client.application.app_context():
        user = User(username="ticketowner", password="hash", role="user", is_deleted=False)
        db.session.add(user)
        db.session.commit()
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            priority="High",
            status="Open",
            user_id=user.id,
            is_deleted=False
        )
        db.session.add(ticket)
        db.session.commit()
        assert ticket.user.username == "ticketowner"
        assert len(user.tickets) == 1

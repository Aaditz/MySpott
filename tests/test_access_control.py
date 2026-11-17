"""Tests for who may open which pages, and for the friendly error pages."""

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now
from app.services import auth_service
from app.web.permissions import admin_required, owner_required, roles_required, verified_required
from tests.helpers import GOOD_PASSWORD, create_user, log_in, page

NEW_PASSWORD = "a-brand-new-password"


def add_test_pages(app):
    """Test-only pages, each protected by one of the checks."""

    @app.get("/_owner")
    @owner_required
    def owner_page():
        return "owner page"

    @app.get("/_admin")
    @admin_required
    def admin_page():
        return "admin page"

    @app.get("/_either")
    @roles_required("owner", "admin")
    def either_page():
        return "either page"

    @app.get("/_verified")
    @verified_required
    def verified_page():
        return "verified page"

    @app.get("/api/v1/_admin_only")
    @admin_required
    def api_admin_page():
        return {"ok": True}


def make_admin(email="admin@example.com"):
    return auth_service.create_admin("Site Admin", email, GOOD_PASSWORD)


# ----------------------------------------------------------------------- roles

def test_anonymous_visitors_are_sent_to_the_login_page(app, client):
    add_test_pages(app)

    response = client.get("/_owner")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")
    assert "next=" in response.headers["Location"]


def test_seekers_are_refused_owner_and_admin_pages(app, client):
    add_test_pages(app)
    create_user()
    log_in(client)

    for path in ["/_owner", "/_admin", "/_either"]:
        response = client.get(path)
        assert response.status_code == 403, path
        assert "permission" in response.get_data(as_text=True)


def test_owners_reach_owner_pages_but_not_admin_pages(app, client):
    add_test_pages(app)
    create_user(role="owner")
    log_in(client)

    assert client.get("/_owner").status_code == 200
    assert client.get("/_either").status_code == 200
    assert client.get("/_admin").status_code == 403


def test_admins_reach_admin_pages_but_are_not_automatically_owners(app, client):
    add_test_pages(app)
    make_admin()
    log_in(client, email="admin@example.com")

    assert client.get("/_admin").status_code == 200
    assert client.get("/_either").status_code == 200
    assert client.get("/_owner").status_code == 403


# ------------------------------------------------------------ confirmed email

def test_unconfirmed_users_are_asked_to_confirm_their_email(app, client):
    add_test_pages(app)
    create_user()
    log_in(client)

    response = client.get("/_verified")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "confirm your email address first" in page(client, "/")


def test_confirmed_users_may_enter_confirmed_only_pages(app, client):
    add_test_pages(app)
    user = create_user()
    log_in(client)
    user.email_verified_at = utc_now()
    db.session.commit()

    response = client.get("/_verified")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "verified page"


def test_anonymous_visitors_are_sent_to_login_for_confirmed_only_pages(app, client):
    add_test_pages(app)

    response = client.get("/_verified")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")


# ------------------------------------------------------------------ error pages

def test_forbidden_pages_use_a_friendly_page_and_the_api_gets_json(app, client):
    add_test_pages(app)
    create_user()
    log_in(client)

    html = client.get("/_admin")
    api = client.get("/api/v1/_admin_only")

    assert html.status_code == 403
    assert "No access" in html.get_data(as_text=True)
    assert api.status_code == 403
    assert api.get_json() == {"error": "You do not have access to this."}


def test_unknown_pages_show_a_friendly_404_and_the_api_gets_json(client):
    html = client.get("/this-page-does-not-exist")
    api = client.get("/api/v1/this-does-not-exist")

    assert html.status_code == 404
    assert "Page not found" in html.get_data(as_text=True)
    assert api.status_code == 404
    assert api.get_json() == {"error": "Not found."}


# ------------------------------------------------------- sessions after changes

def test_a_password_reset_logs_the_user_out_on_every_other_device(app, client):
    user = create_user()
    other_device = app.test_client()
    log_in(client)
    log_in(other_device)
    assert "Hi, Ada Lovelace" in page(client, "/")
    assert "Hi, Ada Lovelace" in page(other_device, "/")

    raw_token = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)
    auth_service.reset_password(raw_token, NEW_PASSWORD)

    for device in (client, other_device):
        home = page(device, "/")
        assert "Hi, Ada Lovelace" not in home
        assert "Log in" in home


def test_a_suspended_user_is_logged_out_at_once(client):
    user = create_user()
    log_in(client)
    assert "Hi, Ada Lovelace" in page(client, "/")

    user.account_status = "suspended"
    db.session.commit()

    assert "Hi, Ada Lovelace" not in page(client, "/")
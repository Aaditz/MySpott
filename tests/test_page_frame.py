"""Tests for the shared page frame: header, menu, footer and the design files."""

from tests.helpers import create_user, log_in, page

FRAME_PIECES = [
    '<html lang="en">',
    'name="viewport"',
    "/static/css/app.css",
    '<main id="main"',
    'href="#main"',
    "data-nav-toggle",
    'aria-label="Main"',
    '<footer class="site-footer">',
]


def test_the_design_files_are_served(client):
    css = client.get("/static/css/app.css")
    script = client.get("/static/js/app.js")
    icon = client.get("/static/img/favicon.svg")

    assert css.status_code == 200
    assert "--color-primary" in css.get_data(as_text=True)
    assert script.status_code == 200
    assert "data-nav-toggle" in script.get_data(as_text=True)
    assert icon.status_code == 200
    assert "<svg" in icon.get_data(as_text=True)


def test_every_kind_of_page_has_the_shared_frame(client):
    for path in ["/", "/auth/login", "/auth/register", "/auth/forgot-password", "/no-such-page"]:
        html = page(client, path)
        for piece in FRAME_PIECES:
            assert piece in html, f"{piece!r} is missing on {path}"


def test_visitors_see_log_in_and_sign_up_and_members_see_their_name_and_log_out(client):
    visitor = page(client, "/")
    assert "Log in" in visitor
    assert "Sign up" in visitor
    assert "Log out" not in visitor

    create_user()
    log_in(client)
    member = page(client, "/")
    assert "Hi, Ada Lovelace" in member
    assert "Log out" in member
    assert "Sign up" not in member


def test_the_menu_marks_the_page_you_are_on(client):
    login = page(client, "/auth/login")
    register = page(client, "/auth/register")
    home = page(client, "/")

    assert 'href="/auth/login" aria-current="page"' in login
    assert 'href="/auth/register" aria-current="page"' in register
    assert "aria-current" not in home


def test_the_home_page_invites_visitors_and_tells_members_listings_are_coming(client):
    assert "Create a free account" in page(client, "/")

    create_user()
    log_in(client)
    member = page(client, "/")
    assert "Listings are coming soon" in member
    assert "Create a free account" not in member


def test_the_phone_menu_is_labelled_and_closed_until_opened(client):
    html = page(client, "/")

    assert 'id="main-menu"' in html
    assert 'aria-controls="main-menu"' in html
    assert 'aria-expanded="false"' in html
    assert 'data-open="false"' in html
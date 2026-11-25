"""Tests for the component kit: messages, confirmation dialog, empty/loading states, style guide."""

import re

from flask import render_template_string

from app.web.dev import dev_pages_enabled
from tests.helpers import page, post_form, register_via_page

STYLE_GUIDE = "/dev/style-guide"


def render(app, template_text):
    """Render a snippet of template text inside a request, like a real page would."""
    with app.test_request_context("/"):
        return render_template_string(template_text)


def test_every_page_has_the_confirmation_dialog_with_cancel_selected_first(client):
    for path in ["/", "/auth/login", "/auth/register", "/no-such-page"]:
        html = page(client, path)
        assert 'id="confirm-dialog"' in html, path
        assert 'method="dialog"' in html, path
        assert re.search(r'<button[^>]*value="cancel"[^>]*autofocus', html), path
        assert 'value="confirm"' in html, path
        assert "data-confirm-accept" in html, path


def test_messages_can_be_closed(client):
    register_via_page(client)

    home = page(client, "/")

    assert "We sent a confirmation link" in home
    assert "data-dismissible" in home
    assert 'aria-label="Dismiss message"' in home
    assert "data-dismiss>" in home or "data-dismiss " in home


def test_the_style_guide_shows_every_component(client):
    response = client.get(STYLE_GUIDE)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    for piece in [
        "swatch--primary", "swatch--danger", "btn btn-danger", "field__error", 'aria-invalid="true"',
        "flash success", "flash warning", "form-alert", "badge badge-highlight", "tag-list",
        "property-card", "empty-state", "skeleton-card", "data-confirm=", 'name="robots"',
    ]:
        assert piece in html, piece


def test_the_demo_confirmation_button_posts_safely(client):
    response = post_form(client, "/dev/style-guide/demo-delete", {}, form_page=STYLE_GUIDE)

    assert response.status_code == 302
    assert response.headers["Location"] == STYLE_GUIDE
    assert "Demo confirmed" in page(client, STYLE_GUIDE)
    assert client.post("/dev/style-guide/demo-delete").status_code == 400  # no CSRF token


def test_the_style_guide_is_only_for_development_and_testing():
    assert dev_pages_enabled({"DEBUG": True}) is True
    assert dev_pages_enabled({"TESTING": True}) is True
    assert dev_pages_enabled({"DEBUG": False, "TESTING": False}) is False
    assert dev_pages_enabled({}) is False


def test_the_confirm_form_macro_is_safe(app):
    html = render(
        app,
        '{% from "components/ui.html" import confirm_form with context %}'
        '{{ confirm_form("/delete/7", "Delete <b>this</b>?", "Delete listing") }}',
    )

    assert 'method="post"' in html
    assert 'action="/delete/7"' in html
    assert 'data-confirm="Delete &lt;b&gt;this&lt;/b&gt;?"' in html  # typed text is escaped
    assert 'name="csrf_token"' in html
    assert 'btn btn-danger' in html


def test_the_empty_state_and_property_card_macros_escape_their_text(app):
    html = render(
        app,
        '{% from "components/ui.html" import empty_state, property_card with context %}'
        '{{ empty_state("<script>x</script>", "Nothing here", "/go", "Go") }}'
        '{{ property_card("<b>Flat</b>", "₹18,500", "Kothanur", ["Furnished"], "New", "/homes/1") }}',
    )

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "&lt;b&gt;Flat&lt;/b&gt;" in html
    assert 'href="/homes/1"' in html
    assert "₹18,500" in html
    assert "Furnished" in html


def test_the_loading_placeholder_is_announced_politely(app):
    html = render(app, '{% from "components/ui.html" import skeleton_card with context %}{{ skeleton_card() }}')

    assert 'role="status"' in html
    assert "Loading" in html
    assert 'aria-hidden="true"' in html


def test_the_style_guide_has_no_inline_styles_or_scripts(client):
    html = page(client, STYLE_GUIDE)

    assert ' style="' not in html
    assert re.search(r"<script(?![^>]*\bsrc=)", html) is None


def test_the_script_knows_about_the_dialog_and_closable_messages(client):
    script = client.get("/static/js/app.js").get_data(as_text=True)

    assert "data-confirm" in script
    assert "showModal" in script
    assert "data-dismiss" in script
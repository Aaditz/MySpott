"""Rules every template must follow, checked across all of them.

These protect pages that do not exist yet: a new template that breaks a rule fails here.
"""

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"


def all_templates():
    files = sorted(TEMPLATES.rglob("*.html"))
    assert files, "no templates found"
    return [(path.relative_to(TEMPLATES).as_posix(), path.read_text(encoding="utf-8")) for path in files]


def test_no_template_uses_inline_styles():
    for name, text in all_templates():
        assert not re.search(r"\sstyle\s*=", text), f"{name} has an inline style; use a class in app.css"


def test_no_template_has_an_inline_script():
    for name, text in all_templates():
        for tag in re.findall(r"<script\b[^>]*>", text):
            assert re.search(r"\bsrc\s*=", tag), f"{name} has an inline script; put it in app.js"


def test_every_form_that_posts_has_a_security_token():
    for name, text in all_templates():
        for form in re.findall(r"<form\b[^>]*>.*?</form>", text, re.S):
            opening = re.match(r"<form\b[^>]*>", form).group(0)
            if re.search(r'method\s*=\s*"post"', opening, re.I):
                assert "csrf_token" in form, f"a POST form in {name} has no csrf_token field"


def test_every_button_says_what_kind_it_is():
    for name, text in all_templates():
        for tag in re.findall(r"<button\b[^>]*>", text):
            assert re.search(r"\btype\s*=", tag), f"{name} has a <button> without a type: {tag}"


def test_every_image_has_alternative_text():
    for name, text in all_templates():
        for tag in re.findall(r"<img\b[^>]*>", text):
            assert re.search(r"\balt\s*=", tag), f"{name} has an <img> without alt text"
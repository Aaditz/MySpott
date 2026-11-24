"""Checks on the design system's stylesheet: the approved colours and readable text."""

import re
from pathlib import Path

CSS_PATH = Path(__file__).resolve().parent.parent / "app" / "static" / "css" / "app.css"

APPROVED = {
    "color-primary": "#0E7C86",
    "color-primary-hover": "#0B656D",
    "color-primary-tint": "#E6F4F5",
    "color-highlight": "#F5B83D",
    "color-ink": "#1F2937",
    "color-muted": "#566070",
    "color-page": "#F7F8FA",
    "color-border": "#E3E7EC",
}

# (text colour, background colour): every pair that really appears on the site.
TEXT_ON_BACKGROUND = [
    ("color-ink", "color-surface"),
    ("color-ink", "color-page"),
    ("color-ink", "color-highlight"),
    ("color-muted", "color-surface"),
    ("color-muted", "color-page"),
    ("color-muted", "color-primary-tint"),
    ("color-on-primary", "color-primary"),
    ("color-on-primary", "color-primary-hover"),
    ("color-on-primary", "color-danger"),
    ("color-primary", "color-surface"),
    ("color-primary", "color-page"),
    ("color-primary-hover", "color-primary-tint"),
    ("color-success", "color-success-tint"),
    ("color-warning", "color-warning-tint"),
    ("color-danger", "color-danger-tint"),
    ("color-danger", "color-surface"),
]


def read_css():
    return CSS_PATH.read_text(encoding="utf-8")


def read_tokens():
    root = re.search(r":root\s*\{(.*?)\n\}", read_css(), re.S).group(1)
    return dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", root))


def luminance(hex_colour):
    digits = hex_colour.lstrip("#")
    channels = [int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(colour_a, colour_b):
    lighter, darker = sorted((luminance(colour_a), luminance(colour_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_brand_colours_match_the_approved_look():
    tokens = read_tokens()

    for name, expected in APPROVED.items():
        assert tokens[name].upper() == expected, name


def test_every_text_and_background_pair_is_easy_to_read():
    tokens = read_tokens()

    for text, background in TEXT_ON_BACKGROUND:
        ratio = contrast(tokens[text], tokens[background])
        assert ratio >= 4.5, f"{text} on {background} is only {ratio:.2f}:1"


def test_every_variable_the_stylesheet_uses_is_defined():
    tokens = read_tokens()
    used = set(re.findall(r"var\(--([a-z0-9-]+)\)", read_css()))

    assert used, "the stylesheet should use its variables"
    assert used <= set(tokens), sorted(used - set(tokens))


def test_the_stylesheet_has_balanced_braces():
    css = read_css()

    assert css.count("{") == css.count("}")
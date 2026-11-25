"""Development-only pages. They are never registered in production."""

from flask import Blueprint, flash, redirect, render_template, url_for

dev_bp = Blueprint("dev", __name__, url_prefix="/dev")


def dev_pages_enabled(config):
    """True while developing or testing, False in production."""
    return bool(config.get("DEBUG") or config.get("TESTING"))


@dev_bp.get("/style-guide")
def style_guide():
    """Every MySpott component on one page, for checking the design by eye."""
    return render_template("dev/style_guide.html")


@dev_bp.post("/style-guide/demo-delete")
def demo_delete():
    """Target of the demo confirmation button. Nothing is really deleted."""
    flash("Demo confirmed: nothing was really deleted.", "success")
    return redirect(url_for("dev.style_guide"))
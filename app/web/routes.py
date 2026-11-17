from flask import render_template

from . import web


@web.get("/")
def home():
    return render_template("home.html")
from flask import Blueprint, render_template

view_bp = Blueprint("view", __name__)

@view_bp.route("/")
def index():
    return render_template("index.html")

@view_bp.route("/apply")
def apply():
    return render_template("apply.html")

@view_bp.route("/admin")
def admin():
    return render_template("admin_dashboard.html")

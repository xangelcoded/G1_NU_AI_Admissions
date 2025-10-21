from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from . import db, User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("login.html"), 401
        session["uid"] = user.id
        session["is_admin"] = bool(user.is_admin)
        if user.must_change_password:
            flash("Please change your password (temporary password in use).", "warning")
        return redirect(url_for("view.admin"))
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("view.index"))

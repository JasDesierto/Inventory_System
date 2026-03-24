from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from .models import User
from .security import is_safe_redirect_target

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
        else:
            # Marking the session permanent applies the configured cookie lifetime to authenticated users.
            session.permanent = True
            login_user(user)
            flash(f"Welcome back, {user.full_name}.", "success")
            if next_url and is_safe_redirect_target(next_url):
                return redirect(next_url)
            return redirect(url_for("inventory.dashboard"))

    has_users = User.query.count() > 0
    return render_template("auth/login.html", has_users=has_users, next_url=next_url)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

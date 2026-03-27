from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from .extensions import db
from .models import User
from .security import is_safe_redirect_target

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or request.form.get("next")
    active_auth_panel = request.args.get("mode", "login")
    if active_auth_panel not in {"login", "signup"}:
        active_auth_panel = "login"
    login_username = ""
    signup_full_name = ""
    signup_username = ""

    if request.method == "POST":
        action = request.form.get("auth_action", "login")
        if action == "signup":
            active_auth_panel = "signup"
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("signup_username", "").strip()
            password = request.form.get("signup_password", "")
            signup_full_name = full_name
            signup_username = username

            existing_user = User.query.filter_by(username=username).first() if username else None

            if not full_name:
                flash("Name is required.", "danger")
            elif not username:
                flash("Username is required.", "danger")
            elif " " in username:
                flash("Username must not contain spaces.", "danger")
            elif len(username) < 3:
                flash("Username must be at least 3 characters long.", "danger")
            elif existing_user:
                flash("That username is already in use.", "danger")
            elif len(password) < 8:
                flash("Password must be at least 8 characters long.", "danger")
            else:
                user = User(
                    username=username,
                    full_name=full_name,
                    role="staff",
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

                session.permanent = True
                login_user(user)
                flash(f"Account created. Welcome, {user.full_name}.", "success")
                if next_url and is_safe_redirect_target(next_url):
                    return redirect(next_url)
                return redirect(url_for("inventory.dashboard"))
        else:
            active_auth_panel = "login"
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            login_username = username
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
    return render_template(
        "auth/login.html",
        active_auth_panel=active_auth_panel,
        has_users=has_users,
        login_username=login_username,
        next_url=next_url,
        signup_full_name=signup_full_name,
        signup_username=signup_username,
    )


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

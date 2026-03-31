from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from .extensions import db
from .models import User
from .security import (
    clear_login_failures,
    consume_signup_attempt,
    format_retry_after,
    is_safe_redirect_target,
    login_retry_after,
    register_login_failure,
    validate_password_strength,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Login and self-signup share one route so the landing page can swap panels
    # without duplicating form templates or redirect logic.
    next_url = request.args.get("next") or request.form.get("next")
    active_auth_panel = request.args.get("mode", "login")
    allow_self_signup = current_app.config["ALLOW_SELF_SIGNUP"]
    if active_auth_panel not in {"login", "signup"}:
        active_auth_panel = "login"
    if active_auth_panel == "signup" and not allow_self_signup:
        active_auth_panel = "login"
    login_username = ""
    signup_full_name = ""
    signup_username = ""

    if request.method == "POST":
        action = request.form.get("auth_action", "login")
        if action == "signup":
            if not allow_self_signup:
                flash("Self-service signup is disabled. Contact an administrator for an account.", "warning")
                return redirect(url_for("auth.login", next=next_url or None, mode="login"))

            active_auth_panel = "signup"
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("signup_username", "").strip()
            password = request.form.get("signup_password", "")
            signup_full_name = full_name
            signup_username = username
            retry_after = consume_signup_attempt()

            if retry_after:
                flash(
                    f"Too many signup attempts from this connection. Try again in {format_retry_after(retry_after)}.",
                    "danger",
                )
                return (
                    render_template(
                        "auth/login.html",
                        active_auth_panel=active_auth_panel,
                        has_users=User.query.count() > 0,
                        login_username=login_username,
                        next_url=next_url,
                        signup_full_name=signup_full_name,
                        signup_username=signup_username,
                    ),
                    429,
                )

            existing_user = User.query.filter_by(username=username).first() if username else None
            password_error = validate_password_strength(password)

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
            elif password_error:
                flash(password_error, "danger")
            else:
                user = User(
                    username=username,
                    full_name=full_name,
                    role="staff",
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

                # Clearing the session before login avoids carrying any stale
                # anonymous-session data into the authenticated session.
                session.clear()
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
            retry_after = login_retry_after(username)
            if retry_after:
                flash(
                    f"Too many sign-in attempts. Try again in {format_retry_after(retry_after)}.",
                    "danger",
                )
                return (
                    render_template(
                        "auth/login.html",
                        active_auth_panel=active_auth_panel,
                        has_users=User.query.count() > 0,
                        login_username=login_username,
                        next_url=next_url,
                        signup_full_name=signup_full_name,
                        signup_username=signup_username,
                    ),
                    429,
                )
            user = User.query.filter_by(username=username).first()

            if not user or not user.check_password(password):
                register_login_failure(username)
                flash("Invalid username or password.", "danger")
            else:
                # Marking the session permanent applies the configured cookie lifetime to authenticated users.
                clear_login_failures(username)
                session.clear()
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
    # Logout always clears the Flask-Login state and the session-backed CSRF
    # token in one step.
    logout_user()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

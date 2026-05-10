from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for
from flask_socketio import emit, join_room

from app import socketio

# Browser pages and WebSocket room setup for logged-in users.
views_bp = Blueprint("views", __name__)


def login_required_page(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapper


@views_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("views.dashboard"))
    return redirect(url_for("auth.login"))


@views_bp.route("/dashboard")
@login_required_page
def dashboard():
    return render_template("dashboard.html", username=session.get("username"))


@socketio.on("connect")
def handle_connect():
    if "user_id" in session:
        join_room(f"user-{session['user_id']}")
        emit("notification", {"message": "Connected to live task updates."})

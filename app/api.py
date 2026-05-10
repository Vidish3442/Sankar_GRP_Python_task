from functools import wraps

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request, session

from app import db, socketio
from app.models import Task

# REST API routes for tasks, analytics, and live updates.
api_bp = Blueprint("api", __name__)

ALLOWED_PRIORITIES = {"Low", "Medium", "High"}
ALLOWED_STATUSES = {"Pending", "In Progress", "Completed"}


def login_required_json(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapper


def _current_user_id():
    return int(session["user_id"])


def _task_or_404(task_id):
    return Task.query.filter_by(id=task_id, user_id=_current_user_id()).first_or_404()


def _validate_task_payload(data, partial=False):
    errors = {}

    if not partial or "title" in data:
        if not str(data.get("title", "")).strip():
            errors["title"] = "Title is required."

    if "priority" in data and data["priority"] not in ALLOWED_PRIORITIES:
        errors["priority"] = "Priority must be Low, Medium, or High."

    if "status" in data and data["status"] not in ALLOWED_STATUSES:
        errors["status"] = "Status must be Pending, In Progress, or Completed."

    return errors


def _emit_task_update(action, task=None):
    payload = {"action": action}
    if task:
        payload["task"] = task.to_dict()
    socketio.emit(f"task_{action}", payload, room=f"user-{_current_user_id()}")


@api_bp.route("/tasks", methods=["GET"])
@login_required_json
def get_tasks():
    tasks = Task.query.filter_by(user_id=_current_user_id()).order_by(Task.created_date.desc()).all()
    return jsonify([task.to_dict() for task in tasks])


@api_bp.route("/tasks", methods=["POST"])
@login_required_json
def add_task():
    data = request.get_json(silent=True) or {}
    errors = _validate_task_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    task = Task(
        title=data["title"].strip(),
        description=data.get("description", "").strip(),
        priority=data.get("priority", "Medium"),
        status=data.get("status", "Pending"),
        user_id=_current_user_id(),
    )
    db.session.add(task)
    db.session.commit()

    _emit_task_update("created", task)
    return jsonify(task.to_dict()), 201


@api_bp.route("/tasks/<int:task_id>", methods=["PUT", "PATCH"])
@login_required_json
def update_task(task_id):
    task = _task_or_404(task_id)
    data = request.get_json(silent=True) or {}
    errors = _validate_task_payload(data, partial=True)
    if errors:
        return jsonify({"errors": errors}), 400

    for field in ("title", "description", "priority", "status"):
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(task, field, value)

    db.session.commit()
    _emit_task_update("updated", task)
    return jsonify(task.to_dict())


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@login_required_json
def delete_task(task_id):
    task = _task_or_404(task_id)
    serialized = task.to_dict()
    db.session.delete(task)
    db.session.commit()

    socketio.emit("task_deleted", {"action": "deleted", "task": serialized}, room=f"user-{_current_user_id()}")
    return jsonify({"message": "Task deleted successfully", "task": serialized})


@api_bp.route("/analytics", methods=["GET"])
@login_required_json
def analytics():
    tasks = Task.query.filter_by(user_id=_current_user_id()).all()
    frame = pd.DataFrame([task.to_dict() for task in tasks])

    total_tasks = int(len(frame))
    if total_tasks == 0:
        completed_tasks = 0
        pending_tasks = 0
        completion_percentage = 0.0
    else:
        statuses = frame["status"].to_numpy()
        completed_tasks = int(np.sum(statuses == "Completed"))
        pending_tasks = int(np.sum(statuses != "Completed"))
        completion_percentage = round(float((completed_tasks / total_tasks) * 100), 2)

    return jsonify(
        {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_percentage": completion_percentage,
        }
    )

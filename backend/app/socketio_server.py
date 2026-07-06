from flask_socketio import SocketIO, emit, join_room
from flask import request
from flask_jwt_extended import decode_token
from bson import ObjectId
from app.database import get_db

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
connected = {}


@socketio.on("connect")
def on_connect():
    token = request.args.get("token")
    if not token:
        return False
    try:
        decoded = decode_token(token)
        uid = decoded["sub"]
        db = get_db()
        user = db.users.find_one({"_id": ObjectId(uid)})
        if not user:
            return False
        join_room(uid)
        connected[request.sid] = {
            "user_id": uid,
            "full_name": user.get("full_name", ""),
            "role": user.get("role", ""),
        }
        _broadcast_online()
        count = db.notifications.count_documents(
            {"user_id": ObjectId(uid), "read": False}
        )
        emit("notification_badge", {"count": count})
        emit("connected", {"user_id": uid})
        return True
    except Exception:
        return False


@socketio.on("disconnect")
def on_disconnect():
    connected.pop(request.sid, None)
    _broadcast_online()


@socketio.on("request_badge")
def on_request_badge():
    for sid, info in connected.items():
        if sid == request.sid:
            db = get_db()
            count = db.notifications.count_documents(
                {"user_id": ObjectId(info["user_id"]), "read": False}
            )
            emit("notification_badge", {"count": count})
            break


def _broadcast_online():
    ids = list({u["user_id"] for u in connected.values()})
    emit("online_users", {"user_ids": ids}, broadcast=True)


def notify_user(user_id, notification_data):
    socketio.emit("notification", notification_data, room=user_id, skip_sid=None)


def notify_badge_update(user_id):
    db = get_db()
    count = db.notifications.count_documents(
        {"user_id": ObjectId(user_id), "read": False}
    )
    socketio.emit("notification_badge", {"count": count}, room=user_id, skip_sid=None)


def get_online_user_ids():
    return list({u["user_id"] for u in connected.values()})

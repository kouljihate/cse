from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.audit_service import AuditService
from app.models.audit import AuditLogResponse
from functools import wraps

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@audit_bp.route("/logs", methods=["GET"])
@jwt_required()
@admin_required
def get_logs():
    raw = request.args.get("entity_type", "")
    entity_types = [t.strip() for t in raw.split(",") if t.strip()] if raw else None
    entity_id = request.args.get("entity_id")
    limit = int(request.args.get("limit", 100))
    skip = int(request.args.get("skip", 0))

    logs = AuditService.get_logs(
        entity_types=entity_types,
        entity_id=entity_id,
        limit=limit,
        skip=skip,
    )
    total = AuditService.count_logs(
        entity_types=entity_types,
        entity_id=entity_id,
    )

    return jsonify({
        "total": total,
        "logs": [AuditLogResponse(**log).model_dump(by_alias=True) for log in logs],
    }), 200

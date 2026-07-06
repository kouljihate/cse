from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from functools import wraps
from app.database import get_db
from app.models.company import CompanySettingsUpdate, CompanySettingsResponse
from app.services.audit_service import AuditService

company_bp = Blueprint("company", __name__, url_prefix="/api/company")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@company_bp.route("/settings", methods=["GET"])
@jwt_required()
def get_settings():
    db = get_db()
    settings = db.company_settings.find_one()
    if not settings:
        return jsonify({"error": "Company settings not found"}), 404
    return jsonify(CompanySettingsResponse.from_mongo(settings).model_dump(by_alias=True)), 200


@company_bp.route("/settings", methods=["POST"])
def save_settings():
    db = get_db()
    existing = db.company_settings.find_one()

    if existing:
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        admin_id = get_jwt_identity()
    else:
        admin_id = "system"

    data = request.get_json()

    try:
        settings_data = CompanySettingsUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    now = datetime.now(timezone.utc)
    settings_dict = settings_data.model_dump(by_alias=True)

    if existing:
        settings_dict["updated_at"] = now
        db.company_settings.update_one({}, {"$set": settings_dict})

        AuditService.log(
            action="update",
            entity_type="company_settings",
            entity_id=str(existing["_id"]),
            performed_by=admin_id,
            description="Company settings updated",
        )
    else:
        settings_dict["created_at"] = now
        settings_dict["updated_at"] = now
        result = db.company_settings.insert_one(settings_dict)
        settings_dict["_id"] = str(result.inserted_id)

        AuditService.log(
            action="create",
            entity_type="company_settings",
            entity_id=str(result.inserted_id),
            performed_by=admin_id,
            description="Company settings created",
        )

    updated = db.company_settings.find_one()
    return jsonify(CompanySettingsResponse.from_mongo(updated).model_dump(by_alias=True)), 200

import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from werkzeug.utils import secure_filename
from functools import wraps
from app.database import get_db
from app.models.document import DocumentCreate, DocumentResponse
from app.services.audit_service import AuditService

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

DOCUMENTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "documents")
)
ALLOWED_EXT = {"pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024

os.makedirs(DOCUMENTS_DIR, exist_ok=True)


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@documents_bp.route("/", methods=["GET"])
@jwt_required()
def list_documents():
    db = get_db()
    customer_id = request.args.get("customer_id")
    service_id = request.args.get("service_id")

    query = {}
    if customer_id:
        query["customer_id"] = ObjectId(customer_id)
    if service_id:
        query["service_id"] = ObjectId(service_id)

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "customer_id",
                "foreignField": "_id",
                "as": "customer",
            }
        },
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "services",
                "localField": "service_id",
                "foreignField": "_id",
                "as": "service",
            }
        },
        {"$unwind": {"path": "$service", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "customer_name": "$customer.full_name",
                "service_name": "$service.name",
            }
        },
        {"$project": {"customer": 0, "service": 0}},
    ]

    docs = list(db.documents.aggregate(pipeline))
    result = []
    for d in docs:
        if "_id" in d and isinstance(d["_id"], ObjectId):
            d["_id"] = str(d["_id"])
        for key in ("customer_id", "service_id", "uploaded_by"):
            if key in d and isinstance(d[key], ObjectId):
                d[key] = str(d[key])
        result.append(d)
    return jsonify(result), 200


@documents_bp.route("/<document_id>", methods=["GET"])
@jwt_required()
def get_document(document_id):
    db = get_db()
    doc = db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    for key in ("customer_id", "service_id", "uploaded_by"):
        if key in doc and isinstance(doc[key], ObjectId):
            doc[key] = str(doc[key])
    return jsonify(doc), 200


@documents_bp.route("/<document_id>/file", methods=["GET"])
@jwt_required()
def get_document_file(document_id):
    from flask import send_file
    db = get_db()
    doc = db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    file_path = doc.get("stored_path")
    if not file_path or not os.path.isfile(file_path):
        return jsonify({"error": "File not found on disk"}), 404
    return send_file(file_path, mimetype=doc.get("mime_type", "application/pdf"))


@documents_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def upload_document():
    db = get_db()
    admin_id = get_jwt_identity()

    customer_id = request.form.get("customer_id", "").strip()
    service_id = request.form.get("service_id", "").strip()
    description = request.form.get("description", "").strip() or None
    file = request.files.get("file")

    if not customer_id:
        return jsonify({"error": "Customer is required"}), 400
    if not service_id:
        return jsonify({"error": "Service is required"}), 400
    if not file or not file.filename:
        return jsonify({"error": "File is required"}), 400

    customer = db.users.find_one({"_id": ObjectId(customer_id), "role": "customer"})
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    service = db.services.find_one({"_id": ObjectId(service_id)})
    if not service:
        return jsonify({"error": "Service not found"}), 404

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Only PDF files are allowed"}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": "File exceeds maximum size of 50MB"}), 400

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M%S")
    safe_name = secure_filename(file.filename)
    stored_name = f"{ts}_{safe_name}"

    folder_path = os.path.join(DOCUMENTS_DIR, customer_id, service_id)
    os.makedirs(folder_path, exist_ok=True)
    stored_path = os.path.join(folder_path, stored_name)

    file.save(stored_path)

    doc_dict = {
        "customer_id": ObjectId(customer_id),
        "service_id": ObjectId(service_id),
        "original_name": file.filename,
        "stored_path": stored_path,
        "file_size": file_size,
        "mime_type": "application/pdf",
        "description": description,
        "uploaded_by": ObjectId(admin_id),
        "created_at": now,
        "updated_at": now,
    }
    result = db.documents.insert_one(doc_dict)
    doc_dict["_id"] = str(result.inserted_id)
    doc_dict["customer_id"] = customer_id
    doc_dict["service_id"] = service_id
    doc_dict["uploaded_by"] = admin_id
    doc_dict["customer_name"] = customer.get("full_name")
    doc_dict["service_name"] = service.get("name")

    AuditService.log(
        action="create",
        entity_type="document",
        entity_id=str(result.inserted_id),
        performed_by=admin_id,
        description=f"Document '{file.filename}' uploaded for customer {customer.get('full_name')}",
    )

    return jsonify(doc_dict), 201


@documents_bp.route("/<document_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_document(document_id):
    db = get_db()
    doc = db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    stored_path = doc.get("stored_path")
    if stored_path and os.path.isfile(stored_path):
        try:
            os.remove(stored_path)
            parent = os.path.dirname(stored_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass

    db.documents.delete_one({"_id": ObjectId(document_id)})

    AuditService.log(
        action="delete",
        entity_type="document",
        entity_id=document_id,
        performed_by=get_jwt_identity(),
        description=f"Document '{doc.get('original_name')}' deleted",
    )

    return jsonify({"message": "Document deleted"}), 200

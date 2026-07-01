from io import BytesIO
from datetime import datetime, timezone
from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt
from bson import ObjectId
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from app.database import get_db
from functools import wraps

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


@reports_bp.route("/tasks", methods=["GET"])
@jwt_required()
@admin_required
def tasks_report():
    db = get_db()
    status_filter = request.args.get("status")

    query = {}
    if status_filter:
        query["status"] = status_filter

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "assigned_to",
                "foreignField": "_id",
                "as": "assigned_user",
            }
        },
        {"$unwind": {"path": "$assigned_user", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "affairs",
                "localField": "affair_id",
                "foreignField": "_id",
                "as": "affair",
            }
        },
        {"$unwind": {"path": "$affair", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "users",
                "localField": "created_by",
                "foreignField": "_id",
                "as": "creator",
            }
        },
        {"$unwind": {"path": "$creator", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "assigned_to_name": "$assigned_user.full_name",
                "affair_name": "$affair.name",
                "created_by_name": "$creator.full_name",
            }
        },
        {"$project": {"assigned_user": 0, "affair": 0, "creator": 0}},
    ]

    tasks = list(db.tasks.aggregate(pipeline))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Cabinet Services Express", styles["Title"]))
    elements.append(Paragraph("Tasks Report", styles["Heading2"]))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 10 * mm))

    data = [["Title", "Affair", "Assigned To", "Priority", "Status", "Due Date"]]
    for t in tasks:
        due = t.get("due_date", "")
        if isinstance(due, datetime):
            due = due.strftime("%Y-%m-%d")
        data.append([
            t.get("title", ""),
            t.get("affair_name", ""),
            t.get("assigned_to_name", ""),
            t.get("priority", ""),
            t.get("status", ""),
            str(due),
        ])

    table = Table(data, colWidths=[100, 80, 80, 60, 60, 70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8eaf6")]),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"tasks_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    )


@reports_bp.route("/affairs", methods=["GET"])
@jwt_required()
@admin_required
def affairs_report():
    db = get_db()
    affairs = list(db.affairs.find().sort("name", 1))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Cabinet Services Express", styles["Title"]))
    elements.append(Paragraph("Affairs Report", styles["Heading2"]))
    elements.append(Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 10 * mm))

    data = [["Name", "Type", "Customer ID", "Status"]]
    for a in affairs:
        data.append([
            a.get("name", ""),
            a.get("affair_type", ""),
            str(a.get("customer_id", "")),
            "Active",
        ])

    table = Table(data, colWidths=[140, 80, 140, 60])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#e8eaf6")]),
    ]))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"affairs_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    )

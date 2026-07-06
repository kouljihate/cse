import os
import re
import subprocess
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from functools import wraps
from werkzeug.utils import secure_filename
from app.services.audit_service import AuditService

requests_bp = Blueprint("requests", __name__, url_prefix="/api/requests")

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REQUESTS_DIR = os.path.join(PROJECT_ROOT, "requests")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


def _parse_request_folder(folder_name):
    folder_path = os.path.join(REQUESTS_DIR, folder_name)
    if not os.path.isdir(folder_path):
        return None
    md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
    if not md_files:
        return None
    md_file = md_files[0]
    md_path = os.path.join(folder_path, md_file)
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else folder_name
    date_match = re.search(r"\*\*Date:\*\*\s+(.+)", content)
    date_str = date_match.group(1).strip() if date_match else ""
    image_count = sum(
        1 for f in os.listdir(folder_path)
        if f.lower().endswith(tuple(ALLOWED_EXT))
    )
    return {
        "foldername": folder_name,
        "title": title,
        "date": date_str,
        "image_count": image_count,
    }


def _run_git(cmd, cwd):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Git operation timed out"
    except FileNotFoundError:
        return False, "", "Git executable not found"
    except Exception as e:
        return False, "", str(e)


def _generate_foldername():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"R-{ts}"


def _save_uploaded_files(files, folder_path):
    saved = []
    for i, file in enumerate(files, 1):
        if file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in ALLOWED_EXT:
                continue
            safe_name = f"image_{i}.{ext}"
            file.save(os.path.join(folder_path, safe_name))
            saved.append(safe_name)
    return saved


@requests_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required
def list_requests():
    if not os.path.isdir(REQUESTS_DIR):
        return jsonify([])
    folders = sorted(
        (d for d in os.listdir(REQUESTS_DIR) if os.path.isdir(os.path.join(REQUESTS_DIR, d))),
        key=lambda d: os.path.getmtime(os.path.join(REQUESTS_DIR, d)),
        reverse=True,
    )
    result = []
    for folder in folders:
        parsed = _parse_request_folder(folder)
        if parsed:
            result.append(parsed)
    return jsonify(result)


@requests_bp.route("/<foldername>", methods=["GET"])
@jwt_required()
@admin_required
def get_request_detail(foldername):
    folder_path = os.path.join(REQUESTS_DIR, foldername)
    if not os.path.isdir(folder_path):
        return jsonify({"error": "Request not found"}), 404

    md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
    if not md_files:
        return jsonify({"error": "Request markdown file not found"}), 404

    md_file = md_files[0]
    md_path = os.path.join(folder_path, md_file)
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read request file: {str(e)}"}), 500

    images = []
    for fname in sorted(os.listdir(folder_path)):
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext in ALLOWED_EXT:
            images.append(f"/api/requests/{foldername}/image/{fname}")

    parsed = _parse_request_folder(foldername)
    return jsonify({
        "foldername": foldername,
        "title": parsed["title"] if parsed else foldername,
        "date": parsed["date"] if parsed else "",
        "markdown": md_content,
        "images": images,
    })


@requests_bp.route("/<foldername>/image/<imagename>")
@jwt_required()
@admin_required
def get_request_image(foldername, imagename):
    from flask import send_file
    image_path = os.path.join(REQUESTS_DIR, foldername, imagename)
    if not os.path.isfile(image_path):
        return jsonify({"error": "Image not found"}), 404
    return send_file(image_path)


@requests_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create_request():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    files = request.files.getlist("screenshots")

    if not title:
        return jsonify({"error": "Title is required"}), 400
    if not content:
        return jsonify({"error": "Content is required"}), 400

    admin_id = get_jwt_identity()
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")
    foldername = _generate_foldername()
    folder_path = os.path.join(REQUESTS_DIR, foldername)

    os.makedirs(folder_path, exist_ok=True)

    image_refs = ""
    if files:
        saved_images = _save_uploaded_files(files, folder_path)
        if saved_images:
            image_refs = "\n\n## Screenshots\n\n" + "\n".join(
                f"![Screenshot {i+1}]({name})" for i, name in enumerate(saved_images)
            )

    md_content = f"""# {title}

**Date:** {now_str}
**Author:** Admin

---

{content}{image_refs}
"""

    md_filename = f"{foldername}.md"
    md_path = os.path.join(folder_path, md_filename)
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    except IOError as e:
        return jsonify({"error": f"Failed to write file: {str(e)}"}), 500

    ok, out, err = _run_git(["git", "add", os.path.join("requests", foldername)], PROJECT_ROOT)
    if not ok:
        return jsonify({"error": f"Git add failed: {err}"}), 500

    ok, out, err = _run_git(["git", "commit", "-m", f"Add request: {title}"], PROJECT_ROOT)
    if not ok:
        return jsonify({"error": f"Git commit failed: {err}"}), 500

    ok, out, err = _run_git(["git", "push"], PROJECT_ROOT)
    if not ok:
        return jsonify({"warning": f"Folder saved and committed but push failed: {err}"}), 201

    AuditService.log(
        action="create",
        entity_type="request",
        entity_id=foldername,
        performed_by=admin_id,
        description=f"Request '{title}' created and pushed to GitHub",
    )

    return jsonify({"ok": True, "foldername": foldername, "message": "Request created and pushed to GitHub"}), 201

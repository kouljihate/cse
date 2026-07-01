from datetime import datetime, timezone
from typing import Any, Optional
from app.database import get_db
from bson import ObjectId


class AuditService:

    @staticmethod
    def log(
        action: str,
        entity_type: str,
        entity_id: str,
        performed_by: str,
        changes: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
    ):
        db = get_db()
        entry = {
            "action": action,
            "entity_type": entity_type,
            "entity_id": ObjectId(entity_id) if ObjectId.is_valid(entity_id) else entity_id,
            "performed_by": ObjectId(performed_by) if ObjectId.is_valid(performed_by) else performed_by,
            "changes": changes or {},
            "description": description or f"{action} on {entity_type}",
            "created_at": datetime.now(timezone.utc),
        }
        db.audit_logs.insert_one(entry)

    @staticmethod
    def get_logs(
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ):
        db = get_db()
        query = {}
        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = ObjectId(entity_id) if ObjectId.is_valid(entity_id) else entity_id

        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "performed_by",
                    "foreignField": "_id",
                    "as": "performer",
                }
            },
            {"$unwind": {"path": "$performer", "preserveNullAndEmptyArrays": True}},
            {
                "$addFields": {
                    "performed_by_name": "$performer.full_name",
                }
            },
            {"$project": {"performer": 0}},
        ]
        return list(db.audit_logs.aggregate(pipeline))

    @staticmethod
    def count_logs(entity_type: Optional[str] = None, entity_id: Optional[str] = None) -> int:
        db = get_db()
        query = {}
        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = ObjectId(entity_id) if ObjectId.is_valid(entity_id) else entity_id
        return db.audit_logs.count_documents(query)

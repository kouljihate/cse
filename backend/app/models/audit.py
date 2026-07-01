from datetime import datetime
from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    performed_by: str
    changes: Optional[dict[str, Any]] = None
    description: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str = Field(alias="_id")
    action: str
    entity_type: str
    entity_id: str
    performed_by: str
    performed_by_name: Optional[str] = None
    changes: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_object_id(cls, data):
        if isinstance(data, dict):
            for key in ("_id", "entity_id", "performed_by"):
                if key in data and isinstance(data[key], ObjectId):
                    data[key] = str(data[key])
        return data

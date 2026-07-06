from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class DocumentCreate(BaseModel):
    customer_id: str
    service_id: str
    description: Optional[str] = None


class DocumentUpdate(BaseModel):
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str = Field(alias="_id")
    customer_id: str
    service_id: str
    service_name: Optional[str] = None
    customer_name: Optional[str] = None
    original_name: str
    stored_path: str
    file_size: int
    mime_type: str
    description: Optional[str] = None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True

    @classmethod
    def from_mongo(cls, doc: dict) -> "DocumentResponse":
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        for key in ("customer_id", "service_id", "uploaded_by"):
            if key in doc and isinstance(doc[key], ObjectId):
                doc[key] = str(doc[key])
        return cls(**doc)

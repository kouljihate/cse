from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: bool = True


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


class ServiceResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    is_active: bool
    task_ids: list[str] = []
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_object_id(cls, data):
        if isinstance(data, dict):
            if "_id" in data and isinstance(data["_id"], ObjectId):
                data["_id"] = str(data["_id"])
            if "task_ids" in data and data["task_ids"]:
                data["task_ids"] = [
                    str(t) if isinstance(t, ObjectId) else t
                    for t in data["task_ids"]
                ]
        return data

from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "cancelled"] = "pending"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]] = None


class TaskResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: Optional[str] = None
    created_by: str
    status: str
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_object_id(cls, data):
        if isinstance(data, dict):
            for key in ("_id", "created_by"):
                if key in data and isinstance(data[key], ObjectId):
                    data[key] = str(data[key])
        return data

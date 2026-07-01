from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    assigned_to: str = Field(..., description="User ID of employee")
    affair_id: str = Field(..., description="Affair ID")
    service_id: Optional[str] = None
    activity_id: Optional[str] = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["pending", "in_progress", "completed", "cancelled"] = "pending"
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    service_id: Optional[str] = None
    activity_id: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]] = None
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: Optional[str] = None
    assigned_to: str
    assigned_to_name: Optional[str] = None
    affair_id: str
    affair_name: Optional[str] = None
    service_id: Optional[str] = None
    service_name: Optional[str] = None
    activity_id: Optional[str] = None
    activity_name: Optional[str] = None
    created_by: str
    priority: str
    status: str
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_object_id(cls, data):
        if isinstance(data, dict):
            for key in ("_id", "assigned_to", "affair_id", "created_by", "service_id", "activity_id"):
                if key in data and isinstance(data[key], ObjectId):
                    data[key] = str(data[key])
        return data
